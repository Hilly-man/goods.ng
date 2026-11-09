"""Goods Flex credit profile: verification steps, credit limit, and the one-running-plan rule.

A customer can only apply once they have a verified phone, a verified BVN, a connected bank account
and a guarantor who has consented. Workplace verification is optional and raises the limit.

Limit = min(statement limit, verification-tier cap, repayment-history cap, lender maximum)

  statement limit   affordability from 6 months of bank transactions (credit.py)
  tier cap          BVN + bank → tier1_max; + verified employment → tier2_max
  history cap       first_plan_cap × (1 + growth_per_completed_plan × plans repaid)
  lender maximum    absolute ceiling set by the lending partner

All thresholds live in PlatformSetting "flex_rules" (admin-editable) with the defaults below.
"""

import hashlib
import hmac
import re
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, Conflict, Forbidden, NotFound
from app.core.security import clean_text, encrypt_field, new_opaque_token, sha256
from app.core.time import utcnow
from app.integrations.bankdata import PERSONAS, get_bank_data_provider
from app.integrations.identity import get_identity_provider, names_match
from app.models import (
    BankConnection,
    BnplApplication,
    CreditAssessment,
    FinancingAgreement,
    FlexProfile,
    Guarantor,
    PlatformSetting,
    User,
)
from app.models.enums import BnplStatus
from app.modules.bnpl import credit
from app.modules.notifications.service import notify, send_direct

DEFAULT_RULES = {
    "max_dti": "0.33",
    "tier1_max": "300000",
    "tier2_max": "1500000",
    "lender_max": "3000000",
    "first_plan_cap": "500000",
    "growth_per_completed_plan": "0.5",
    "assessment_valid_days": 90,
    "down_payment_rate": "0.30",
    "monthly_charge_rate": "0.035",
    "max_tenor_months": 6,
    "max_active_guarantees": 3,
}
RUNNING = (BnplStatus.APPROVED, BnplStatus.ACCEPTED, BnplStatus.ACTIVE, BnplStatus.DEFAULTED)
FREE_EMAIL_DOMAINS = {"gmail.com", "yahoo.com", "yahoo.co.uk", "hotmail.com", "outlook.com", "live.com", "icloud.com",
                      "aol.com", "ymail.com", "proton.me", "protonmail.com", "mail.com", "gmx.com", "zoho.com"}
CAC_RE = re.compile(r"^(RC|BN|IT|LP)?\s?\d{5,8}$", re.I)


def rules(db: Session) -> dict:
    row = db.get(PlatformSetting, "flex_rules")
    return {**DEFAULT_RULES, **(row.value if row else {})}


def policy(db: Session) -> credit.Policy:
    r = rules(db)
    return credit.Policy(max_dti=Decimal(str(r["max_dti"])), down_payment_rate=Decimal(str(r["down_payment_rate"])),
                         monthly_charge_rate=Decimal(str(r["monthly_charge_rate"])), max_tenor_months=int(r["max_tenor_months"]))


def profile(db: Session, user: User) -> FlexProfile:
    p = db.scalars(select(FlexProfile).where(FlexProfile.user_id == user.id)).first()
    if not p:
        p = FlexProfile(user_id=user.id)
        db.add(p)
        db.flush()
    return p


def bvn_fingerprint(bvn: str) -> str:
    return hmac.new(settings.otp_secret.encode(), f"bvn:{bvn}".encode(), hashlib.sha256).hexdigest()


# ---------------- one running plan ----------------
def running_plan(db: Session, user_id) -> BnplApplication | None:
    """The customer's current plan (approved-but-unaccepted offers that have expired are released first)."""
    from app.modules.bnpl.service import release_application

    for app_ in db.scalars(select(BnplApplication).where(BnplApplication.user_id == user_id,
                                                         BnplApplication.status.in_(RUNNING))).all():
        if app_.status == BnplStatus.APPROVED and app_.offer_expires_at and app_.offer_expires_at < utcnow():
            release_application(db, app_, "Financing offer expired")
            continue
        return app_
    return None


def completed_plans(db: Session, user_id) -> int:
    return db.scalar(select(func.count()).select_from(FinancingAgreement).join(BnplApplication).where(
        BnplApplication.user_id == user_id, FinancingAgreement.status == BnplStatus.COMPLETED)) or 0


def latest_assessment(db: Session, user_id) -> CreditAssessment | None:
    return db.scalars(select(CreditAssessment).where(CreditAssessment.user_id == user_id,
                                                     CreditAssessment.expires_at > utcnow())
                      .order_by(CreditAssessment.created_at.desc())).first()


def active_guarantor(db: Session, user_id) -> Guarantor | None:
    return db.scalars(select(Guarantor).where(Guarantor.user_id == user_id,
                                              Guarantor.status.in_(["pending_consent", "consented"]))
                      .order_by(Guarantor.created_at.desc())).first()


# ---------------- limit ----------------
def credit_limit(db: Session, user: User, *, assume_guarantor: bool = False) -> dict:
    """The customer's limit. `assume_guarantor` previews the limit if a guarantor consents."""
    r = rules(db)
    p = profile(db, user)
    a = latest_assessment(db, user.id)
    g = active_guarantor(db, user.id)
    bvn_ok = p.bvn_verified_at is not None
    emp_ok = p.employment_verified_at is not None
    actual_guar_ok = bool(g and g.status == "consented")
    guar_ok = actual_guar_ok or assume_guarantor
    tier1, tier2, lender_max = (Decimal(str(r[k])) for k in ("tier1_max", "tier2_max", "lender_max"))
    tier_cap = Decimal("0") if not (bvn_ok and guar_ok) else (tier2 if emp_ok else tier1)
    done = completed_plans(db, user.id)
    history_cap = (Decimal(str(r["first_plan_cap"])) * (1 + Decimal(str(r["growth_per_completed_plan"])) * done))
    statement = a.statement_limit if a else Decimal("0")
    caps = {"statement": statement, "verification": tier_cap, "history": history_cap, "lender": lender_max}
    if actual_guar_ok and g and g.amount_guaranteed is not None:
        # The guarantor only agreed to a specific amount; the limit cannot silently exceed it.
        caps["guarantee"] = g.amount_guaranteed
    limit = min(caps.values()) if (bvn_ok and a and guar_ok) else Decimal("0")
    binding = min(caps, key=lambda k: caps[k]) if limit > 0 else None
    tips = []
    if not guar_ok:
        if g and g.status == "pending_consent":
            tips.append("Your guarantor still needs to confirm by SMS before you can use Goods Flex")
        else:
            tips.append("Add a guarantor — their consent is required before you can use Goods Flex")
    elif bvn_ok and a:
        if binding == "verification" and not emp_ok:
            tips.append(f"Verify your workplace to raise your cap to ₦{tier2:,.0f}")
        elif binding == "guarantee":
            tips.append(f"Your guarantor agreed to cover up to ₦{g.amount_guaranteed:,.0f}. "
                        "Ask them to re-consent if you need a higher limit")
        elif binding == "history":
            tips.append("Repay your first Goods Flex plan on time to unlock a higher limit")
        elif binding == "statement":
            tips.append("Your limit is based on your income and existing loan repayments")
    steps = {
        "phone": user.phone_verified,
        "bvn": bvn_ok,
        "bank": a is not None,
        "employment": emp_ok,
        "guarantor": "consented" if actual_guar_ok else (g.status if g else None),
    }
    return {"limit": limit, "caps": caps, "binding_cap": binding, "steps": steps, "tips": tips,
            "completed_plans": done, "assessment": a}


def guaranteed_amount(db: Session, user: User) -> Decimal:
    """What the guarantor would be guaranteeing if they consent (the borrower's prospective limit)."""
    return credit_limit(db, user, assume_guarantor=True)["limit"]


# ---------------- steps ----------------
def verify_bvn(db: Session, user: User, bvn: str, dob: date | None) -> FlexProfile:
    from app.core.deps import ensure_customer

    ensure_customer(user)
    if not user.phone_verified:
        raise AppError("Verify your phone number first", code="phone_unverified")
    if not re.fullmatch(r"\d{11}", bvn):
        raise AppError("BVN must be 11 digits", code="validation_error", status_code=422,
                       details=[{"field": "bvn", "message": "BVN must be 11 digits"}])
    p = profile(db, user)
    fp = bvn_fingerprint(bvn)
    other = db.scalars(select(FlexProfile).where(FlexProfile.bvn_fingerprint == fp, FlexProfile.user_id != user.id)).first()
    if other:
        raise Conflict("This BVN is already linked to another Goods.ng account", code="bvn_in_use")
    rec = get_identity_provider().lookup_bvn(bvn, hint_name=user.full_name, hint_phone=user.phone, hint_dob=dob)
    if not rec.found:
        raise AppError("We couldn't find that BVN. Please check the number.", code="bvn_not_found")
    if not names_match(rec.full_name, user.full_name):
        raise AppError("The name on this BVN doesn't match your account name. Update your profile name to match your bank records.",
                       code="bvn_name_mismatch")
    p.bvn_enc, p.bvn_last4, p.bvn_fingerprint = encrypt_field(bvn), bvn[-4:], fp
    p.bvn_name, p.bvn_reference, p.bvn_verified_at = rec.full_name, rec.reference, utcnow()
    p.bvn_phone_match = bool(rec.phone and user.phone and rec.phone[-10:] == user.phone[-10:])
    db.commit()
    return p


def connect_bank(db: Session, user: User, code: str) -> CreditAssessment:
    from app.core.deps import ensure_customer

    ensure_customer(user)
    p = profile(db, user)
    if not p.bvn_verified_at:
        raise AppError("Verify your BVN before connecting a bank account", code="bvn_required")
    provider = get_bank_data_provider()
    acct = provider.exchange_code(code, account_name=p.bvn_name or user.full_name)
    if not names_match(acct.account_name, p.bvn_name or user.full_name):
        raise AppError("The bank account must be in your own name", code="bank_name_mismatch")
    conn = BankConnection(user_id=user.id, provider=provider.name, provider_account_ref=acct.provider_account_ref,
                          bank_name=acct.bank_name, account_name=acct.account_name,
                          account_number_last4=acct.account_number_last4)
    db.add(conn)
    db.flush()
    result = credit.assess(provider.transactions(acct.provider_account_ref, months=6), policy(db))
    r = rules(db)
    a = CreditAssessment(user_id=user.id, bank_connection_id=conn.id, engine_version=credit.ENGINE_VERSION,
                         months_analysed=result.months_analysed, monthly_income=result.monthly_income,
                         income_source=result.income_source, monthly_debt=result.monthly_loan_repayments,
                         affordable_instalment=result.affordable_instalment, statement_limit=result.statement_limit,
                         score=result.score, metrics=result.as_json(),
                         expires_at=utcnow() + timedelta(days=int(r["assessment_valid_days"])))
    db.add(a)
    _maybe_verify_self_employment(p, a)
    db.commit()
    return a


def _maybe_verify_self_employment(p: FlexProfile, a: CreditAssessment | None) -> None:
    """Self-employed: CAC number + business inflows visible in the bank statement."""
    if p.employment_type in ("self_employed", "business_owner") and p.cac_number and not p.employment_verified_at:
        if a and a.monthly_income > 0:
            p.employment_verified_at, p.employment_method = utcnow(), "cac_and_statement"


def save_employment(db: Session, user: User, data: dict) -> tuple[FlexProfile, str | None]:
    p = profile(db, user)
    kind = data["employment_type"]
    p.employment_type = kind
    p.employer_name = clean_text(data.get("employer_name"))
    p.job_title = clean_text(data.get("job_title"))
    p.monthly_income_declared = data.get("monthly_income_declared")
    p.employment_verified_at = p.employment_method = None
    link = None
    if kind == "employed":
        email = (data.get("work_email") or "").strip().lower()
        if not p.employer_name:
            raise AppError("Enter your employer's name", code="validation_error", status_code=422,
                           details=[{"field": "employer_name", "message": "Enter your employer's name"}])
        if "@" not in email or email.split("@")[-1] in FREE_EMAIL_DOMAINS:
            raise AppError("Use your official work email (not Gmail, Yahoo, etc.)", code="validation_error", status_code=422,
                           details=[{"field": "work_email", "message": "Use your official work email"}])
        token = new_opaque_token()
        p.work_email, p.work_email_token_hash = email, sha256(token)
        p.work_email_token_expires = utcnow() + timedelta(hours=24)
        link = f"{settings.frontend_url}/flex/verify-work-email?token={token}"
        send_direct(db, "email", email, f"Confirm your workplace for Goods Flex: {link}\n\nIf you didn't request this, ignore this email.",
                    subject="Confirm your work email", event_type="flex_workplace", link=link,
                    recipient_name=user.full_name)
    else:
        cac = (data.get("cac_number") or "").strip().upper()
        if not CAC_RE.match(cac):
            raise AppError("Enter a valid CAC registration number (e.g. RC123456 or BN1234567)", code="validation_error",
                           status_code=422, details=[{"field": "cac_number", "message": "Enter a valid CAC number"}])
        p.cac_number = cac
        _maybe_verify_self_employment(p, latest_assessment(db, user.id))
    db.commit()
    return p, link


def verify_work_email(db: Session, user: User, token: str) -> FlexProfile:
    p = profile(db, user)
    if not p.work_email_token_hash or p.work_email_token_hash != sha256(token):
        raise AppError("This link is invalid or has already been used", code="token_invalid")
    if p.work_email_token_expires and p.work_email_token_expires < utcnow():
        raise AppError("This link has expired. Request a new one.", code="token_expired")
    p.employment_verified_at, p.employment_method = utcnow(), "work_email"
    p.work_email_token_hash = None
    db.commit()
    return p


def add_guarantor(db: Session, user: User, data: dict) -> tuple[Guarantor, str]:
    p = profile(db, user)
    if not p.bvn_verified_at:
        raise AppError("Verify your own BVN first", code="bvn_required")
    if latest_assessment(db, user.id) is None:
        raise AppError("Connect your bank account before adding a guarantor", code="bank_required")
    if data["phone"] == user.phone:
        raise AppError("Your guarantor must be someone else", code="guarantor_self")
    fp = bvn_fingerprint(data["bvn"])
    if fp == p.bvn_fingerprint:
        raise AppError("Your guarantor must be someone else", code="guarantor_self")
    r = rules(db)
    active = db.scalar(select(func.count()).select_from(Guarantor).where(
        Guarantor.bvn_fingerprint == fp, Guarantor.user_id != user.id,
        Guarantor.status.in_(["pending_consent", "consented"]))) or 0
    if active >= int(r["max_active_guarantees"]):
        raise AppError("This person is already guaranteeing the maximum number of Goods Flex customers. "
                       "Please ask someone else.", code="guarantor_limit_reached")
    rec = get_identity_provider().lookup_bvn(data["bvn"], hint_name=data["full_name"], hint_phone=data["phone"], hint_dob=None)
    if not rec.found or not names_match(rec.full_name, data["full_name"]):
        raise AppError("We couldn't verify your guarantor's BVN against their name", code="guarantor_bvn_mismatch")
    for old in db.scalars(select(Guarantor).where(Guarantor.user_id == user.id,
                                                  Guarantor.status.in_(["pending_consent", "consented"]))).all():
        old.status = "revoked"
    token = new_opaque_token()
    amount = guaranteed_amount(db, user)
    g = Guarantor(user_id=user.id, full_name=clean_text(data["full_name"]), phone=data["phone"],
                  relationship_to_user=clean_text(data["relationship"]), bvn_enc=encrypt_field(data["bvn"]),
                  bvn_last4=data["bvn"][-4:], bvn_reference=rec.reference, bvn_fingerprint=fp,
                  amount_guaranteed=amount, consent_token_hash=sha256(token),
                  consent_expires_at=utcnow() + timedelta(days=7))
    db.add(g)
    link = f"{settings.frontend_url}/guarantor/{token}"
    guarantee = f"up to ₦{amount:,.0f}" if amount > 0 else "for their Goods Flex account"
    send_direct(db, "sms", data["phone"],
                f"Goods.ng: {user.full_name} has asked you to be their guarantor for Goods Flex purchases {guarantee}. "
                f"Review and respond: {link}")
    db.commit()
    return g, link


def cancel_guarantor(db: Session, user: User) -> None:
    g = active_guarantor(db, user.id)
    if not g:
        raise NotFound("You don't have an active guarantor request")
    g.status = "revoked"
    db.commit()


def resend_guarantor(db: Session, user: User) -> tuple[Guarantor, str]:
    g = active_guarantor(db, user.id)
    if not g or g.status != "pending_consent":
        raise AppError("There is no pending guarantor request to resend", code="guarantor_not_pending")
    token = new_opaque_token()
    amount = guaranteed_amount(db, user)
    g.consent_token_hash, g.consent_expires_at = sha256(token), utcnow() + timedelta(days=7)
    g.amount_guaranteed = amount
    link = f"{settings.frontend_url}/guarantor/{token}"
    guarantee = f"up to ₦{amount:,.0f}" if amount > 0 else "for their Goods Flex account"
    send_direct(db, "sms", g.phone,
                f"Goods.ng: reminder — {user.full_name} has asked you to be their guarantor for Goods Flex purchases {guarantee}. "
                f"Review and respond: {link}")
    db.commit()
    return g, link


def guarantor_by_token(db: Session, token: str) -> Guarantor:
    g = db.scalars(select(Guarantor).where(Guarantor.consent_token_hash == sha256(token))).first()
    if not g:
        raise NotFound("This guarantor request is invalid or has been withdrawn")
    if g.status == "pending_consent" and g.consent_expires_at and g.consent_expires_at < utcnow():
        g.status = "expired"
        db.commit()
    return g


def guarantor_respond(db: Session, token: str, agree: bool, ip: str) -> Guarantor:
    g = guarantor_by_token(db, token)
    if g.status != "pending_consent":
        raise Forbidden(f"This request is {g.status.replace('_', ' ')}", code="guarantor_closed")
    g.status = "consented" if agree else "declined"
    g.consented_at, g.consent_ip = (utcnow(), ip) if agree else (None, None)
    notify(db, g.user_id, "guarantor_response", "Guarantor update",
           f"{g.full_name} has {'agreed to be your guarantor' if agree else 'declined to be your guarantor'}. "
           + ("Check your Goods Flex page for your available limit." if agree else "You can ask someone else."),
           link="/flex")
    db.commit()
    return g


def ensure_can_apply(db: Session, user: User, amount: Decimal) -> dict:
    """Raises if the customer can't take this Flex purchase; returns the limit info otherwise."""
    # Serialise applications per customer (pairs with the partial unique index on running plans).
    db.query(User).filter_by(id=user.id).with_for_update().one()
    running = running_plan(db, user.id)
    if running:
        raise Conflict("You already have a Goods Flex plan running. You can start a new one once it's fully paid.",
                       code="bnpl_plan_running", details={"application_id": str(running.id)})
    info = credit_limit(db, user)
    if info["limit"] <= 0:
        missing = [k for k in ("phone", "bvn", "bank") if not info["steps"][k]]
        if info["steps"]["guarantor"] != "consented":
            missing.append("guarantor")
        raise AppError("Set up Goods Flex first: verify your phone and BVN, connect your bank account and add a guarantor.",
                       code="flex_not_ready", details={"missing": missing})
    if amount > info["limit"]:
        raise AppError(f"This purchase (₦{amount:,.0f}) is above your Goods Flex limit of ₦{info['limit']:,.0f}.",
                       code="flex_limit_exceeded", details={"limit": f"{info['limit']:.2f}", "amount": f"{amount:.2f}"})
    return info


def is_running_conflict(exc: IntegrityError) -> bool:
    return "uq_bnpl_one_running_plan" in str(exc.orig)


__all__ = ["PERSONAS"]
