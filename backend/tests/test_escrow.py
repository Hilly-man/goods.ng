import threading
from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.core.db import SessionLocal
from app.core.time import utcnow
from app.integrations.payments.mock import MockPaymentProvider
from app.models import EscrowTransaction, LedgerTransaction, Order
from app.modules.ledger import service as ledger
from app.modules.orders import service as orders
from tests.conftest import ADDRESS, simulate_payment


def _ledger_ok(db):
    tb = ledger.trial_balance(db)
    assert tb["balanced"], tb


def test_full_protected_checkout_lifecycle(db, paid_order):
    buyer, seller, product, order = paid_order()
    assert order["status"] == "awaiting_seller"
    timeline = [e["to"] for e in order["escrow"]["timeline"]]
    assert timeline == ["pending_payment", "payment_confirmed", "funds_safeguarded", "awaiting_seller"]
    # 1.5M + 3.5k courier + 5k protection
    assert order["total"] == "1508500.00"
    assert buyer.get(f"/products/{product['slug']}").json()["quantity"] == 1  # stock reserved

    oid = order["id"]
    assert seller.post(f"/orders/{oid}/accept").json()["status"] == "processing"
    r = seller.post(f"/orders/{oid}/dispatch", {"carrier": "GIG Logistics"})
    assert r.json()["error"]["code"] == "tracking_required"  # courier requires tracking
    r = seller.post(f"/orders/{oid}/dispatch", {"carrier": "GIG Logistics", "tracking_reference": "GIG123456"})
    assert r.json()["status"] == "dispatched"
    pin = buyer.get(f"/orders/{oid}").json()["delivery"]["delivery_pin"]
    assert pin and len(pin) == 6
    r = seller.post(f"/orders/{oid}/delivered", {"evidence_urls": [], "notes": "Handed to buyer", "pin": pin})
    assert r.json()["status"] == "awaiting_buyer_confirmation"
    assert r.json()["escrow"]["release_eligible_at"] is not None
    # Seller cannot confirm on buyer's behalf
    assert seller.post(f"/orders/{oid}/confirm").status_code == 403
    done = buyer.post(f"/orders/{oid}/confirm").json()
    assert done["status"] == "completed"

    # Ledger: seller payable = total - commission(5% of 1.5M) - protection fee
    esc = db.query(EscrowTransaction).filter_by(order_id=oid).one()
    assert esc.platform_amount == Decimal("80000.00")  # 75k commission + 5k protection
    assert ledger.balance(db, ledger.seller_payable(seller.seller["id"])[0]) == Decimal("1428500.00")
    assert ledger.balance(db, ledger.COMMISSION[0]) == Decimal("75000.00")
    assert ledger.balance(db, ledger.PROTECTION_FEES[0]) == Decimal("5000.00")
    assert ledger.balance(db, ledger.ESCROW_OBLIGATIONS[0]) == Decimal("0.00")
    _ledger_ok(db)

    # Second confirmation cannot settle twice
    assert buyer.post(f"/orders/{oid}/confirm").status_code == 409
    assert db.query(LedgerTransaction).filter(LedgerTransaction.idempotency_key.like("escrow:%:settle")).count() == 1


def test_checkout_requires_verified_email_and_phone(make_seller, make_user, make_product):
    seller = make_seller()
    p = make_product(seller)

    unverified_email = make_user(email_verified=False)
    r = unverified_email.post("/checkout", {"product_id": p["id"], "address": ADDRESS})
    assert r.status_code == 403 and r.json()["error"]["code"] == "email_unverified"
    code = unverified_email.post("/auth/email/resend").json()["dev_code"]
    assert unverified_email.post("/auth/email/verify", {"code": code}).status_code == 200
    assert unverified_email.post("/checkout", {"product_id": p["id"], "address": ADDRESS}).status_code == 201

    unverified_phone = make_user(phone_verified=False)
    r = unverified_phone.post("/checkout", {"product_id": p["id"], "address": ADDRESS})
    assert r.status_code == 403 and r.json()["error"]["code"] == "phone_unverified"
    code = unverified_phone.post("/auth/otp/request", {}).json()["dev_code"]
    assert unverified_phone.post("/auth/otp/verify", {"code": code}).status_code == 200
    assert unverified_phone.post("/checkout", {"product_id": p["id"], "address": ADDRESS}).status_code == 201


def test_client_cannot_set_price(db, make_seller, make_user, make_product):
    seller, buyer = make_seller(), make_user()
    p = make_product(seller)
    r = buyer.post("/checkout", {"product_id": p["id"], "address": ADDRESS, "price": "1.00", "total": "1.00",
                                 "unit_price": "1.00"})
    assert r.status_code == 201
    assert r.json()["total"] == "1505000.00"  # server-computed (pickup, no delivery fee)


def test_underpayment_never_funds_order(db, make_seller, make_user, make_product):
    seller, buyer = make_seller(), make_user()
    p = make_product(seller)
    r = buyer.post("/checkout", {"product_id": p["id"], "address": ADDRESS}).json()
    res = simulate_payment(buyer, r["payment_reference"], paid_amount=Decimal("1000.00"))
    assert res["payment_status"] == "failed"
    assert buyer.get(f"/orders/{r['order_id']}").json()["status"] == "pending_payment"
    assert db.query(LedgerTransaction).count() == 0


def test_duplicate_webhook_is_idempotent(client, db, make_seller, make_user, make_product):
    seller, buyer = make_seller(), make_user()
    p = make_product(seller)
    r = buyer.post("/checkout", {"product_id": p["id"], "address": ADDRESS}).json()
    body, headers = MockPaymentProvider.simulate_outcome(r["payment_reference"], "success")
    first = client.post("/api/v1/payments/webhooks/mock/webhook", content=body, headers=headers)
    second = client.post("/api/v1/payments/webhooks/mock/webhook", content=body, headers=headers)
    assert first.json()["status"] == "ok" and second.json()["status"] == "duplicate"
    # a *different* event for the same payment is processed but changes nothing
    body2, headers2 = MockPaymentProvider.simulate_outcome(r["payment_reference"], "success")
    client.post("/api/v1/payments/webhooks/mock/webhook", content=body2, headers=headers2)
    assert db.query(LedgerTransaction).filter(LedgerTransaction.kind == "escrow_funded").count() == 1
    order = buyer.get(f"/orders/{r['order_id']}").json()
    assert [e["to"] for e in order["escrow"]["timeline"]].count("payment_confirmed") == 1


def test_frontend_verify_without_payment_does_nothing(make_seller, make_user, make_product):
    seller, buyer = make_seller(), make_user()
    p = make_product(seller)
    r = buyer.post("/checkout", {"product_id": p["id"], "address": ADDRESS}).json()
    v = buyer.post(f"/payments/{r['payment_reference']}/verify").json()
    assert v["status"] == "initialized"
    assert buyer.get(f"/orders/{r['order_id']}").json()["status"] == "pending_payment"


def test_concurrent_confirmation_settles_once(db, paid_order):
    buyer, seller, _, order = paid_order()
    oid = order["id"]
    seller.post(f"/orders/{oid}/accept")
    seller.post(f"/orders/{oid}/dispatch", {"carrier": "GIG", "tracking_reference": "T1"})
    results = []

    def confirm():
        with SessionLocal() as s:
            from app.models import User

            u = s.get(User, buyer.user["id"])
            try:
                orders.buyer_confirm(s, u, oid)
                results.append("ok")
            except Exception as e:  # noqa: BLE001
                results.append(type(e).__name__)

    threads = [threading.Thread(target=confirm) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results.count("ok") == 1, results
    assert db.query(LedgerTransaction).filter(LedgerTransaction.kind == "escrow_released").count() == 1
    _ledger_ok(db)


def test_stock_cannot_be_oversold(make_seller, make_user, make_product):
    seller = make_seller()
    p = make_product(seller, quantity=1)
    b1, b2 = make_user(), make_user()
    assert b1.post("/checkout", {"product_id": p["id"], "address": ADDRESS}).status_code == 201
    r = b2.post("/checkout", {"product_id": p["id"], "address": ADDRESS})
    assert r.status_code == 409 and r.json()["error"]["code"] == "insufficient_stock"


def test_checkout_idempotency_key(make_seller, make_user, make_product):
    seller, buyer = make_seller(), make_user()
    p = make_product(seller)
    h = {"Idempotency-Key": "abc-123"}
    a = buyer.post("/checkout", {"product_id": p["id"], "address": ADDRESS}, headers=h).json()
    b = buyer.post("/checkout", {"product_id": p["id"], "address": ADDRESS}, headers=h).json()
    assert a["order_id"] == b["order_id"]
    assert buyer.get(f"/products/{p['slug']}").json()["quantity"] == 1


def test_unpaid_order_expires_and_restores_stock(db, make_seller, make_user, make_product):
    seller, buyer = make_seller(), make_user()
    p = make_product(seller, quantity=1)
    r = buyer.post("/checkout", {"product_id": p["id"], "address": ADDRESS}).json()
    db.query(Order).update({"expires_at": utcnow() - timedelta(minutes=1)})
    db.commit()
    assert orders.expire_unpaid(db) == 1
    assert buyer.get(f"/orders/{r['order_id']}").json()["status"] == "cancelled"
    assert buyer.get(f"/products/{p['slug']}").json()["quantity"] == 1


def test_late_payment_after_expiry_is_honoured_when_stock_available(db, make_seller, make_user, make_product):
    seller, buyer = make_seller(), make_user()
    p = make_product(seller, quantity=1)
    r = buyer.post("/checkout", {"product_id": p["id"], "address": ADDRESS}).json()
    db.query(Order).update({"expires_at": utcnow() - timedelta(minutes=1)})
    db.commit()
    # Provider marks it paid but the webhook is late; expiry job checks provider first.
    MockPaymentProvider.simulate_outcome(r["payment_reference"], "success")
    orders.expire_unpaid(db)
    assert buyer.get(f"/orders/{r['order_id']}").json()["status"] == "awaiting_seller"


def test_seller_decline_refunds_buyer_and_restores_stock(db, paid_order):
    buyer, seller, product, order = paid_order()
    r = seller.post(f"/orders/{order['id']}/decline", {"reason": "Out of stock"}).json()
    assert r["status"] == "refunded"
    assert r["refunds"][0]["status"] == "completed"
    assert buyer.get(f"/products/{product['slug']}").json()["quantity"] == 2
    assert ledger.balance(db, ledger.ESCROW_HOLDING[0]) == Decimal("0.00")
    _ledger_ok(db)


def test_dispute_refund_requires_second_admin(db, paid_order, make_admin):
    buyer, seller, _, order = paid_order()
    oid = order["id"]
    seller.post(f"/orders/{oid}/accept")
    seller.post(f"/orders/{oid}/dispatch", {"carrier": "GIG", "tracking_reference": "T1"})
    r = buyer.post(f"/orders/{oid}/disputes", {"reason": "not_as_described",
                                               "description": "The phone is a replica, not the original as advertised."})
    assert r.json()["status"] == "disputed"
    # Buyer can no longer confirm/auto-release while disputed
    assert buyer.post(f"/orders/{oid}/confirm").status_code == 409
    dispute_id = r.json()["disputes"][0]["id"]

    resolver = make_admin(["disputes.resolve", "refunds.approve"])
    approver = make_admin(["refunds.approve"])
    res = resolver.post(f"/admin/disputes/{dispute_id}/resolve",
                        {"outcome": "refund_buyer", "notes": "Evidence confirms item not as described."})
    assert res.status_code == 200
    refund_id = resolver.get("/admin/refunds", params={"status": "pending_approval"}).json()["items"][0]["id"]
    same = resolver.post(f"/admin/refunds/{refund_id}/approve")
    assert same.status_code == 403 and same.json()["error"]["code"] == "four_eyes"
    ok = approver.post(f"/admin/refunds/{refund_id}/approve")
    assert ok.status_code == 200 and ok.json()["status"] == "completed"
    # Duplicate approval is impossible
    assert approver.post(f"/admin/refunds/{refund_id}/approve").status_code == 409
    assert buyer.get(f"/orders/{oid}").json()["status"] == "refunded"
    _ledger_ok(db)
    recon = approver.get("/admin/reconciliation")
    assert recon.status_code == 403  # approver lacks payments.view
    recon = make_admin(["payments.view"]).get("/admin/reconciliation").json()
    assert recon["ledger_balanced"] and recon["obligations_match_open_escrow"]
    assert recon["missing_settlement_entries"] == []


def test_dispute_resolved_for_seller_releases(db, paid_order, make_admin):
    buyer, seller, _, order = paid_order()
    oid = order["id"]
    seller.post(f"/orders/{oid}/accept")
    seller.post(f"/orders/{oid}/dispatch", {"carrier": "GIG", "tracking_reference": "T1"})
    pin = buyer.get(f"/orders/{oid}").json()["delivery"]["delivery_pin"]
    seller.post(f"/orders/{oid}/delivered", {"evidence_urls": [], "pin": pin})
    r = seller.post(f"/orders/{oid}/disputes", {"reason": "buyer_refuses_confirmation",
                                                "description": "Delivered with signed waybill but buyer will not confirm."})
    dispute_id = r.json()["disputes"][0]["id"]
    admin = make_admin(["disputes.resolve"])
    admin.post(f"/admin/disputes/{dispute_id}/resolve", {"outcome": "release_to_seller",
                                                         "notes": "Signed waybill proves delivery."})
    assert buyer.get(f"/orders/{oid}").json()["status"] == "completed"
    _ledger_ok(db)


def test_auto_release_after_window(db, paid_order):
    buyer, seller, _, order = paid_order()
    oid = order["id"]
    seller.post(f"/orders/{oid}/accept")
    seller.post(f"/orders/{oid}/dispatch", {"carrier": "GIG", "tracking_reference": "T1"})
    pin = buyer.get(f"/orders/{oid}").json()["delivery"]["delivery_pin"]
    seller.post(f"/orders/{oid}/delivered", {"evidence_urls": [], "pin": pin})
    assert orders.auto_release_due(db) == 0
    db.query(EscrowTransaction).update({"release_eligible_at": utcnow() - timedelta(seconds=1)})
    db.commit()
    assert orders.auto_release_due(db) == 1
    assert buyer.get(f"/orders/{oid}").json()["status"] == "completed"


def test_invalid_transitions_rejected(paid_order, make_user):
    buyer, seller, _, order = paid_order()
    oid = order["id"]
    assert seller.post(f"/orders/{oid}/dispatch", {"carrier": "x", "tracking_reference": "y"}).status_code == 409
    assert buyer.post(f"/orders/{oid}/accept").status_code == 403
    assert make_user().get(f"/orders/{oid}").status_code == 404  # other users can't see it


def test_ledger_is_append_only(db, paid_order):
    paid_order()
    with pytest.raises(DBAPIError):
        db.execute(text("UPDATE ledger_entries SET amount = 1"))
        db.commit()
    db.rollback()
    with pytest.raises(DBAPIError):
        db.execute(text("DELETE FROM escrow_events"))
        db.commit()
    db.rollback()


def test_unbalanced_ledger_rejected_by_database(db):
    import uuid

    with pytest.raises(DBAPIError):
        acct = ledger.get_account(db, ledger.ESCROW_HOLDING)
        tid = uuid.uuid4()
        db.execute(text("INSERT INTO ledger_transactions (id, idempotency_key, kind, description, meta, created_at) "
                        "VALUES (:id, 'x', 'test', 'test', '{}', now())"), {"id": tid})
        db.execute(text("INSERT INTO ledger_entries (id, transaction_id, account_id, direction, amount, created_at) "
                        "VALUES (:id, :t, :a, 'debit', 100, now())"), {"id": uuid.uuid4(), "t": tid, "a": acct.id})
        db.commit()
    db.rollback()
