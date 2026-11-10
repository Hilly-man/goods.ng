"""Goods Flex: verification steps, bank-statement credit limits, caps and the one-running-plan rule."""

import random
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import BnplApplication, Installment, Notification
from app.modules.bnpl.service import mark_overdue_and_remind
from tests.conftest import ADDRESS, simulate_payment


def new_bvn() -> str:
    while True:
        b = str(random.randint(10**10, 10**11 - 1))
        if not b.startswith("000") and not b.endswith("9999"):
            return b


def token_from(link: str) -> str:
    return link.split("token=")[-1] if "token=" in link else link.rstrip("/").split("/")[-1]


def setup_flex(api, persona="salary_earner", employment=False, guarantor=True):
    r = api.post("/bnpl/profile/bvn", {"bvn": new_bvn()})
    assert r.status_code == 200, r.text
    r = api.post("/bnpl/profile/bank/connect", {"code": f"mock:{persona}:GTBank"})
    assert r.status_code == 200, r.text
    if employment:
        r = api.post("/bnpl/profile/employment", {"employment_type": "employed", "employer_name": "Acme Nigeria Ltd",
                                                  "job_title": "Analyst", "work_email": "ada@acme.com.ng"})
        assert r.status_code == 200, r.text
        r = api.post("/bnpl/profile/employment/verify-email", {"token": token_from(r.json()["dev_link"])})
        assert r.status_code == 200, r.text
    if guarantor:
        r = api.post("/bnpl/profile/guarantor", {"full_name": "Emeka Obi", "phone": "08099990001",
                                                 "relationship": "Brother", "bvn": new_bvn()})
        assert r.status_code == 200, r.text
        assert api.post(f"/bnpl/guarantor/{token_from(r.json()['dev_link'])}", json={"agree": True}).status_code == 200
    return api.get("/bnpl/profile").json()


def apply(buyer, product, tenor=3, **extra):
    return buyer.post("/bnpl/applications", {"product_id": product["id"], "address": ADDRESS, "tenor_months": tenor,
                                             "consent": True, "delivery_option_index": 0, **extra})


def flex_product(make_product, seller, price="200000", **kw):
    return make_product(seller, title=f"Flex phone {random.randint(1, 10**6)}", price=price, bnpl_enabled=True, **kw)


# ---------------- setup & limits ----------------
def test_limit_grows_with_verification_steps(make_user):
    u = make_user()
    s = u.get("/bnpl/profile").json()
    assert s["credit_limit"] == "0.00" and s["steps"]["bvn"] is False and s["can_apply"] is False

    u.post("/bnpl/profile/bvn", {"bvn": new_bvn()})
    assert u.get("/bnpl/profile").json()["credit_limit"] == "0.00"  # bank statement still needed

    r = u.post("/bnpl/profile/bank/connect", {"code": "mock:salary_earner:GTBank"}).json()
    a = r["assessment"]
    assert a["income_source"] == "salary" and a["monthly_income"] == "450000.00" and a["monthly_debt"] == "20000.00"
    assert Decimal(a["statement_limit"]) > Decimal("700000")
    # A guarantor is required: without one there is no usable limit even with a good statement.
    assert r["credit_limit"] == "0.00" and r["steps"]["guarantor"] is None and r["can_apply"] is False
    assert any("guarantor" in t.lower() for t in r["tips"])

    guarantor = {"full_name": "Emeka Obi", "phone": "08099990001", "relationship": "Brother", "bvn": new_bvn()}
    g = u.post("/bnpl/profile/guarantor", guarantor).json()
    assert g["credit_limit"] == "0.00" and g["steps"]["guarantor"] == "pending_consent"
    assert Decimal(g["guarantor"]["amount_guaranteed"]) == Decimal("300000.00")
    assert any("confirm" in t.lower() for t in g["tips"])
    u.post(f"/bnpl/guarantor/{token_from(g['dev_link'])}", json={"agree": True})
    # Guarantor consented, no workplace yet → tier 1.
    r = u.get("/bnpl/profile").json()
    assert r["credit_limit"] == "300000.00" and r["binding_cap"] == "verification" and r["can_apply"] is True
    assert any("workplace" in t for t in r["tips"])

    r = u.post("/bnpl/profile/employment", {"employment_type": "employed", "employer_name": "Acme Nigeria Ltd",
                                            "work_email": "ada@acme.com.ng"}).json()
    assert r["profile"]["employment_pending"] is True and r["credit_limit"] == "300000.00"
    r = u.post("/bnpl/profile/employment/verify-email", {"token": token_from(r["dev_link"])}).json()
    # Employment raises the tier, but the guarantor only agreed to ₦300k until they re-consent.
    assert r["credit_limit"] == "300000.00" and r["binding_cap"] == "guarantee"
    assert any("re-consent" in t for t in r["tips"])

    # Asking again re-computes the amount for the now-higher tier.
    u.delete("/bnpl/profile/guarantor")
    g = u.post("/bnpl/profile/guarantor", {**guarantor, "bvn": new_bvn()}).json()
    assert Decimal(g["guarantor"]["amount_guaranteed"]) == Decimal("500000.00")
    u.post(f"/bnpl/guarantor/{token_from(g['dev_link'])}", json={"agree": True})
    r = u.get("/bnpl/profile").json()
    # Tier 2 (₦1.5M) is available, but the first-plan history cap (₦500k) binds.
    assert r["credit_limit"] == "500000.00" and r["binding_cap"] == "history"


def test_risky_statement_gets_small_limit(make_user):
    s = setup_flex(make_user(), persona="risky")
    a = s["assessment"]
    assert Decimal(a["statement_limit"]) < Decimal("100000")
    assert any("betting" in x for x in a["reasons"]) and any("failed" in x for x in a["reasons"])


def test_irregular_trader_income_is_haircut(make_user):
    a = setup_flex(make_user(), persona="trader")["assessment"]
    assert a["income_source"] == "business_inflows"


# ---------------- one running plan ----------------
def test_only_one_running_plan_until_paid(make_user, make_seller, make_product):
    seller, buyer = make_seller(), make_user()
    setup_flex(buyer)
    p1, p2 = flex_product(make_product, seller), flex_product(make_product, seller)
    a1 = apply(buyer, p1).json()
    assert a1["status"] == "approved"
    blocked = apply(buyer, p2)
    assert blocked.status_code == 409 and blocked.json()["error"]["code"] == "bnpl_plan_running"
    assert buyer.get("/bnpl/profile").json()["can_apply"] is False

    # accept + down payment → plan is active, still blocks
    pay = buyer.post(f"/bnpl/applications/{a1['id']}/accept", {"accept_terms": True}).json()
    simulate_payment(buyer, pay["payment_reference"])
    assert apply(buyer, p2).json()["error"]["code"] == "bnpl_plan_running"

    # pay every instalment → plan completed → a new plan is allowed, with a higher history cap
    ag = buyer.get("/bnpl/agreements").json()["agreements"][0]
    for inst in ag["installments"]:
        simulate_payment(buyer, buyer.post(f"/bnpl/installments/{inst['id']}/pay").json()["payment_reference"])
    prof = buyer.get("/bnpl/profile").json()
    assert prof["running_plan"] is None and prof["completed_plans"] == 1
    assert Decimal(prof["caps"]["history"]) == Decimal("750000")  # 500k × (1 + 0.5 × 1)
    assert apply(buyer, p2).json()["status"] == "approved"


def test_withdrawing_unpaid_application_frees_the_slot(make_user, make_seller, make_product, client):
    seller, buyer = make_seller(), make_user()
    setup_flex(buyer)
    p1 = flex_product(make_product, seller, quantity=1)
    a1 = apply(buyer, p1).json()
    w = buyer.post(f"/bnpl/applications/{a1['id']}/withdraw").json()
    assert w["status"] == "cancelled"
    assert client.get(f"/api/v1/products/{p1['slug']}").json()["quantity"] == 1  # stock released
    assert apply(buyer, p1).json()["status"] == "approved"


def test_expired_offer_releases_slot(db, make_user, make_seller, make_product):
    seller, buyer = make_seller(), make_user()
    setup_flex(buyer)
    a1 = apply(buyer, flex_product(make_product, seller)).json()
    db.query(BnplApplication).filter_by(id=a1["id"]).update({"offer_expires_at": date.today() - timedelta(days=2)})
    db.commit()
    assert apply(buyer, flex_product(make_product, seller)).json()["status"] == "approved"


def test_database_enforces_one_running_plan(db, make_user, make_seller, make_product):
    seller, buyer = make_seller(), make_user()
    setup_flex(buyer)
    a1 = apply(buyer, flex_product(make_product, seller)).json()
    original = db.get(BnplApplication, a1["id"])
    clone = BnplApplication(user_id=original.user_id, product_id=original.product_id, provider="mock",
                            purchase_amount=original.purchase_amount, tenor_months=3, status="accepted")
    db.add(clone)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_default_blocks_new_plans(db, make_user, make_seller, make_product):
    seller, buyer = make_seller(), make_user()
    setup_flex(buyer)
    a1 = apply(buyer, flex_product(make_product, seller)).json()
    pay = buyer.post(f"/bnpl/applications/{a1['id']}/accept", {"accept_terms": True}).json()
    simulate_payment(buyer, pay["payment_reference"])
    first = db.query(Installment).order_by(Installment.sequence).first()
    first.due_date = date.today() - timedelta(days=45)
    db.commit()
    mark_overdue_and_remind(db)
    assert buyer.get("/bnpl/agreements").json()["agreements"][0]["status"] == "defaulted"
    r = apply(buyer, flex_product(make_product, seller))
    assert r.json()["error"]["code"] in ("bnpl_overdue", "bnpl_plan_running")


# ---------------- limit checks at application ----------------
def test_not_ready_and_over_limit(make_user, make_seller, make_product):
    seller, buyer = make_seller(), make_user()
    expensive = make_product(seller, bnpl_enabled=True)  # ₦1.5M
    assert apply(buyer, expensive).json()["error"]["code"] == "flex_not_ready"
    setup_flex(buyer)
    r = apply(buyer, expensive)
    assert r.json()["error"]["code"] == "flex_limit_exceeded" and r.json()["error"]["details"]["limit"] == "300000.00"


def test_guarantor_required_at_application(make_user, make_seller, make_product):
    seller, buyer = make_seller(), make_user()
    buyer.post("/bnpl/profile/bvn", {"bvn": new_bvn()})
    buyer.post("/bnpl/profile/bank/connect", {"code": "mock:salary_earner:GTBank"})
    r = apply(buyer, flex_product(make_product, seller, price="100000"))
    assert r.json()["error"]["code"] == "flex_not_ready"
    assert "guarantor" in r.json()["error"]["details"]["missing"]


def test_full_flow_and_seller_decline(make_user, make_seller, make_product):
    seller, buyer = make_seller(), make_user()
    setup_flex(buyer)
    a = apply(buyer, flex_product(make_product, seller)).json()
    assert a["credit_decision_ref"].startswith("MOCKDEC")
    pay = buyer.post(f"/bnpl/applications/{a['id']}/accept", {"accept_terms": True}).json()
    simulate_payment(buyer, pay["payment_reference"])
    assert buyer.get(f"/orders/{a['order_id']}").json()["status"] == "awaiting_seller"
    seller.post(f"/orders/{a['order_id']}/decline", {"reason": "Out of stock"})
    ag = buyer.get("/bnpl/agreements").json()["agreements"][0]
    assert ag["status"] == "cancelled" and all(i["status"] == "cancelled" for i in ag["installments"])
    assert buyer.get("/bnpl/profile").json()["running_plan"] is None


def test_consent_and_availability(make_user, make_seller, make_product):
    seller, buyer = make_seller(), make_user()
    setup_flex(buyer)
    r = buyer.post("/bnpl/applications", {"product_id": flex_product(make_product, seller)["id"], "address": ADDRESS,
                                          "tenor_months": 3, "consent": False})
    assert r.json()["error"]["code"] == "consent_required"
    off = make_product(seller, price="100000", bnpl_enabled=False, title="No flex phone here")
    assert apply(buyer, off).json()["error"]["code"] == "bnpl_unavailable"


# ---------------- verification safeguards ----------------
def test_bvn_safeguards(make_user):
    u1, u2 = make_user(), make_user()
    assert make_user(phone_verified=False).post("/bnpl/profile/bvn", {"bvn": new_bvn()}).json()["error"]["code"] == "phone_unverified"
    assert u1.post("/bnpl/profile/bvn", {"bvn": "00012345678"}).json()["error"]["code"] == "bvn_not_found"
    assert u1.post("/bnpl/profile/bvn", {"bvn": "12345679999"}).json()["error"]["code"] == "bvn_name_mismatch"
    assert u1.post("/bnpl/profile/bvn", {"bvn": "123"}).status_code == 422
    shared = new_bvn()
    assert u1.post("/bnpl/profile/bvn", {"bvn": shared}).status_code == 200
    assert u2.post("/bnpl/profile/bvn", {"bvn": shared}).json()["error"]["code"] == "bvn_in_use"
    prof = u1.get("/bnpl/profile").json()["profile"]
    assert prof["bvn_last4"] == shared[-4:] and "bvn" not in prof  # never returned in full
    assert make_user().post("/bnpl/profile/bank/connect", {"code": "mock:salary_earner"}).json()["error"]["code"] == "bvn_required"


def test_employment_safeguards(make_user):
    u = make_user()
    u.post("/bnpl/profile/bvn", {"bvn": new_bvn()})
    r = u.post("/bnpl/profile/employment", {"employment_type": "employed", "employer_name": "Acme", "work_email": "ada@gmail.com"})
    assert r.status_code == 422
    assert u.post("/bnpl/profile/employment/verify-email", {"token": "x" * 20}).json()["error"]["code"] == "token_invalid"
    # Self-employed: CAC number + business inflows in the statement
    r = u.post("/bnpl/profile/employment", {"employment_type": "business_owner", "cac_number": "RC1234567"}).json()
    assert r["profile"]["employment_pending"] is True  # no statement yet
    r = u.post("/bnpl/profile/bank/connect", {"code": "mock:trader:Opay"}).json()
    assert r["profile"]["employment_method"] == "cac_and_statement"


def test_guarantor_flow_and_safeguards(make_user, client, db):
    u = make_user()
    u.post("/bnpl/profile/bvn", {"bvn": new_bvn()})
    g = {"full_name": "Emeka Obi", "phone": "08099990002", "relationship": "Brother", "bvn": new_bvn()}
    # The statement must be analysed before a guarantor can be asked to guarantee an amount.
    assert u.post("/bnpl/profile/guarantor", g).json()["error"]["code"] == "bank_required"
    u.post("/bnpl/profile/bank/connect", {"code": "mock:salary_earner:GTBank"})
    r = u.post("/bnpl/profile/guarantor", g).json()
    assert r["steps"]["guarantor"] == "pending_consent"
    assert Decimal(r["guarantor"]["amount_guaranteed"]) == Decimal("300000.00")  # tier 1 before employment

    resent = u.post("/bnpl/profile/guarantor/resend").json()
    tok = token_from(resent["dev_link"])  # resend rotates the token
    view = client.get(f"/api/v1/bnpl/guarantor/{tok}").json()
    assert view["status"] == "pending_consent" and view["borrower_name"] == u.user["full_name"]
    assert view["amount_guaranteed"] == "300000.00"
    assert client.post(f"/api/v1/bnpl/guarantor/{tok}", json={"agree": True}).json()["status"] == "consented"
    assert client.post(f"/api/v1/bnpl/guarantor/{tok}", json={"agree": False}).status_code == 403  # already answered

    notify = db.query(Notification).filter_by(user_id=u.user["id"], event_type="guarantor_response").one()
    assert "agreed to be your guarantor" in notify.body
    prof = u.get("/bnpl/profile").json()
    assert prof["steps"]["guarantor"] == "consented" and prof["credit_limit"] == "300000.00"

    # Cancelling the guarantee immediately takes the limit away.
    prof = u.delete("/bnpl/profile/guarantor").json()
    assert prof["steps"]["guarantor"] is None and prof["credit_limit"] == "0.00"
    assert u.post("/bnpl/profile/guarantor/resend").json()["error"]["code"] == "guarantor_not_pending"

    # Workplace verification still raises the cap once a guarantor consents.
    setup = setup_flex(make_user(), employment=True)
    assert setup["profile"]["employment_verified_at"]
    assert setup["caps"]["verification"] == "1500000.00" and setup["caps"]["lender"] == "3000000.00"

    v = make_user()
    setup_flex(v, employment=True)
    assert v.post("/bnpl/profile/guarantor", {**g, "phone": v.user["phone"]}).json()["error"]["code"] == "guarantor_self"


def test_one_guarantor_cannot_guarantee_unlimited_borrowers(make_user):
    g = {"full_name": "Emeka Obi", "phone": "08099990003", "relationship": "Brother", "bvn": new_bvn()}
    for _ in range(3):
        u = make_user()
        u.post("/bnpl/profile/bvn", {"bvn": new_bvn()})
        u.post("/bnpl/profile/bank/connect", {"code": "mock:salary_earner:GTBank"})
        assert u.post("/bnpl/profile/guarantor", g).status_code == 200
    fourth = make_user()
    fourth.post("/bnpl/profile/bvn", {"bvn": new_bvn()})
    fourth.post("/bnpl/profile/bank/connect", {"code": "mock:salary_earner:GTBank"})
    r = fourth.post("/bnpl/profile/guarantor", g)
    assert r.json()["error"]["code"] == "guarantor_limit_reached"


def test_admin_can_tune_flex_rules(make_user, make_admin):
    admin = make_admin(["settings.manage"])
    rules = admin.get("/admin/settings").json()["flex_rules"]
    assert rules["tier1_max"] == "300000"
    bad = {**{k: rules[k] for k in ("max_dti", "tier2_max", "lender_max", "first_plan_cap", "growth_per_completed_plan")},
           "tier1_max": "2000000", "assessment_valid_days": 90}
    assert admin.put("/admin/settings", {"flex_rules": bad}).status_code == 400
    ok = {**bad, "tier1_max": "200000"}
    assert admin.put("/admin/settings", {"flex_rules": ok}).json()["flex_rules"]["tier1_max"] == "200000"
    u = make_user()
    assert setup_flex(u)["credit_limit"] == "200000.00"  # new tier-1 cap applies immediately
