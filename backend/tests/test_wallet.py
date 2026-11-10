from datetime import timedelta
from decimal import Decimal

from app.core.time import utcnow
from app.models import EscrowTransaction


def _dispatch(buyer, seller, oid):
    seller.post(f"/orders/{oid}/accept")
    r = seller.post(f"/orders/{oid}/dispatch", {"carrier": "GIG", "tracking_reference": "T1"})
    assert r.status_code == 200, r.text
    return buyer.get(f"/orders/{oid}").json()["delivery"]["delivery_pin"]


def test_delivery_pin_is_buyer_only_and_required(paid_order):
    buyer, seller, _, order = paid_order()
    oid = order["id"]
    pin = _dispatch(buyer, seller, oid)
    assert pin and len(pin) == 6
    # The seller never sees the PIN.
    assert seller.get(f"/orders/{oid}").json()["delivery"]["delivery_pin"] is None

    wrong = "000000" if pin != "000000" else "111111"
    r = seller.post(f"/orders/{oid}/delivered", {"evidence_urls": [], "pin": wrong})
    assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_delivery_pin"

    r = seller.post(f"/orders/{oid}/delivered", {"evidence_urls": [], "pin": pin})
    assert r.status_code == 200 and r.json()["status"] == "awaiting_buyer_confirmation"
    # Once used, the PIN is no longer returned.
    assert buyer.get(f"/orders/{oid}").json()["delivery"]["delivery_pin"] is None


def test_delivery_pin_locks_after_five_attempts(paid_order):
    buyer, seller, _, order = paid_order()
    oid = order["id"]
    pin = _dispatch(buyer, seller, oid)
    wrong = "000000" if pin != "000000" else "111111"
    for _ in range(5):
        assert seller.post(f"/orders/{oid}/delivered", {"evidence_urls": [], "pin": wrong}).status_code == 400
    locked = seller.post(f"/orders/{oid}/delivered", {"evidence_urls": [], "pin": pin})
    assert locked.status_code == 400 and locked.json()["error"]["code"] == "delivery_pin_locked"


def test_carrier_webhook_marks_delivered_without_pin(client, db, paid_order):
    from app.core.config import settings

    buyer, seller, _, order = paid_order()
    oid = order["id"]
    _dispatch(buyer, seller, oid)
    body = {"order_reference": order["order_number"], "status": "delivered", "event_key": "evt-1"}
    r = client.post("/api/v1/delivery/webhooks/mock", json=body,
                    headers={"X-Mock-Signature": settings.mock_provider_secret})
    assert r.status_code == 200 and r.json()["updated"] == 1
    assert buyer.get(f"/orders/{oid}").json()["status"] == "awaiting_buyer_confirmation"
    # Bad signature is refused.
    bad = client.post("/api/v1/delivery/webhooks/mock", json={**body, "event_key": "evt-2"},
                      headers={"X-Mock-Signature": "nope"})
    assert bad.status_code == 403


def test_wallet_clears_after_hold_window_and_pays_out(db, paid_order):
    from app.modules.ledger import service as ledger
    from app.modules.wallet import service as wallet

    buyer, seller, _, order = paid_order()
    oid = order["id"]
    pin = _dispatch(buyer, seller, oid)
    seller.post(f"/orders/{oid}/delivered", {"evidence_urls": [], "pin": pin})
    buyer.post(f"/orders/{oid}/confirm")
    amount = Decimal(seller.get(f"/orders/{oid}").json()["seller_earnings"])

    w = seller.get("/seller/wallet").json()
    assert Decimal(w["available"]) == Decimal("0.00")
    assert Decimal(w["clearing"]) == amount
    assert Decimal(w["on_hold"]) == Decimal("0.00")

    # Within the clearing window a withdrawal is refused even though the ledger shows released funds.
    acct = seller.post("/seller/bank-accounts", {"bank_name": "GTBank", "account_name": "Chinedu Okafor",
                                                 "account_number": "0123456789"}).json()
    assert acct["is_default"] and acct["is_verified"] and acct["account_name"] == "Chinedu Okafor"
    assert seller.post("/seller/payouts", {"amount": "1200.00", "bank_account_id": acct["id"]}).status_code == 400

    # Age the release past the 24h clearing window.
    db.query(EscrowTransaction).filter_by(order_id=oid).update(
        {"released_at": utcnow() - timedelta(hours=25)})
    db.commit()
    w = seller.get("/seller/wallet").json()
    assert Decimal(w["available"]) == amount

    r = seller.post("/seller/payouts", {"amount": f"{amount:.2f}", "bank_account_id": acct["id"]},
                    headers={"Idempotency-Key": "wd-1"})
    assert r.status_code == 201, r.text
    payout = r.json()
    assert payout["status"] == "requested"
    # Idempotent retry returns the same payout.
    again = seller.post("/seller/payouts", {"amount": f"{amount:.2f}", "bank_account_id": acct["id"]},
                        headers={"Idempotency-Key": "wd-1"}).json()
    assert again["id"] == payout["id"]
    # Pending payouts reduce "available" immediately; the ledger is only debited when paid.
    assert Decimal(seller.get("/seller/wallet").json()["pending_payouts"]) == amount
    assert Decimal(seller.get("/seller/wallet").json()["available"]) == Decimal("0.00")
    assert ledger.balance(db, ledger.seller_payable(seller.seller["id"])[0]) == amount

    assert wallet.process_due_payouts(db) == 1
    paid = seller.get("/seller/payouts").json()[0]
    assert paid["status"] == "paid"
    assert ledger.balance(db, ledger.seller_payable(seller.seller["id"])[0]) == Decimal("0.00")
    assert ledger.trial_balance(db)["balanced"]


def test_buyer_complaint_freezes_payouts_until_admin_releases(make_admin, db, paid_order):
    buyer, seller, _, order = paid_order()
    oid = order["id"]
    pin = _dispatch(buyer, seller, oid)
    seller.post(f"/orders/{oid}/delivered", {"evidence_urls": [], "pin": pin})
    buyer.post(f"/orders/{oid}/confirm")
    acct = seller.post("/seller/bank-accounts", {"bank_name": "GTBank", "account_name": "Chinedu Okafor",
                                                 "account_number": "0123456789"}).json()
    assert acct

    r = buyer.post(f"/orders/{oid}/complaints", {"description": "The device heats up and the battery health is far below advertised."})
    assert r.status_code == 201, r.text
    assert seller.get("/seller/wallet").json()["payouts_frozen"] is True
    assert seller.post("/seller/payouts", {"amount": "1200.00", "bank_account_id": acct["id"]}).status_code == 403

    # Outside the window a complaint is refused.
    db.query(EscrowTransaction).filter_by(order_id=oid).update(
        {"released_at": utcnow() - timedelta(hours=25)})
    db.commit()
    late = buyer.post(f"/orders/{oid}/complaints", {"description": "This is a late complaint that should not be accepted."})
    assert late.status_code == 409

    admin = make_admin(["disputes.resolve"])
    holds = admin.get("/admin/wallet/holds").json()["items"]
    assert len(holds) == 1
    rel = admin.post(f"/admin/wallet/holds/{holds[0]['id']}/release")
    assert rel.status_code == 200, rel.text
    assert seller.get("/seller/wallet").json()["payouts_frozen"] is False
