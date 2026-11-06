import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Header, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select

from app.core.cache import check_rate_limit
from app.core.config import settings
from app.core.deps import DB, CurrentUser, client_ip
from app.core.errors import AppError, NotFound
from app.core.security import CleanStr
from app.models import BnplApplication, FinancingAgreement, Product
from app.modules.auth.schemas import normalize_ng_phone
from app.modules.bnpl import flex, service
from app.modules.bnpl.flex import PERSONAS
from app.modules.orders.router import Address

router = APIRouter(prefix="/bnpl", tags=["goods flex (bnpl)"])


@router.get("/eligibility")
def eligibility(user: CurrentUser, db: DB):
    return service.eligibility(db, user)


@router.get("/quote")
def quote(product_id: uuid.UUID, db: DB, amount: Decimal | None = None):
    """Illustrative options for a listing. Binding terms are only those returned after applying."""
    p = db.get(Product, product_id)
    if not p or p.deleted_at:
        raise NotFound("Listing not found")
    return {"options": service.quote(db, p, amount or p.price),
            "disclosure": "Indicative only. Final terms are set by the lending partner after an application."}


class ApplyIn(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(1, ge=1, le=10)
    negotiation_id: uuid.UUID | None = None
    delivery_option_index: int = 0
    address: Address
    note: CleanStr | None = Field(None, max_length=500)
    tenor_months: int = Field(ge=1, le=24)
    consent: bool = Field(description="Consent to share application data with the lending partner")
    marketing_consent: bool = False  # buyer accepted marketing cookies (ads measurement)


@router.post("/applications", status_code=201)
def apply(data: ApplyIn, user: CurrentUser, db: DB, idempotency_key: str | None = Header(None, max_length=80)):
    check_rate_limit(f"flex:apply:{user.id}", 10, 3600)
    if not data.consent:
        raise AppError("Consent is required to submit your application to the lending partner", code="consent_required")
    a = service.apply(db, user, product_id=data.product_id, quantity=data.quantity, negotiation_id=data.negotiation_id,
                      delivery_index=data.delivery_option_index, address=data.address.model_dump(), note=data.note,
                      tenor_months=data.tenor_months, idempotency_key=idempotency_key)
    if data.marketing_consent and a.order_id:
        from app.models import Order

        o = db.get(Order, a.order_id)
        if o and not o.marketing_consent:
            o.marketing_consent = True
            db.commit()
    return service.application_out(a)


@router.post("/applications/{application_id}/withdraw")
def withdraw(application_id: uuid.UUID, user: CurrentUser, db: DB):
    return service.application_out(service.withdraw(db, user, application_id))


# ---------------- Flex credit profile ----------------
class BvnIn(BaseModel):
    bvn: str = Field(pattern=r"^\d{11}$")
    date_of_birth: date | None = None


class BankConnectIn(BaseModel):
    code: str = Field(min_length=3, max_length=500)


class EmploymentIn(BaseModel):
    employment_type: Literal["employed", "self_employed", "business_owner"]
    employer_name: str | None = Field(None, max_length=160)
    job_title: str | None = Field(None, max_length=120)
    work_email: str | None = Field(None, max_length=255)
    cac_number: str | None = Field(None, max_length=30)
    monthly_income_declared: Decimal | None = Field(None, ge=0, le=Decimal("1000000000"))


class TokenIn(BaseModel):
    token: str = Field(min_length=10, max_length=200)


class GuarantorIn(BaseModel):
    full_name: CleanStr = Field(min_length=3, max_length=160)
    phone: str
    relationship: CleanStr = Field(min_length=2, max_length=40)
    bvn: str = Field(pattern=r"^\d{11}$")

    @field_validator("phone")
    @classmethod
    def _p(cls, v):
        return normalize_ng_phone(v)


class ConsentIn(BaseModel):
    agree: bool


def _dev(link: str | None) -> dict:
    # Development convenience ONLY: echo email/SMS links so flows can be tested without providers.
    return {"dev_link": link} if link and settings.environment in ("development", "test") else {}


@router.get("/profile")
def flex_profile(user: CurrentUser, db: DB):
    return service.eligibility(db, user)


@router.post("/profile/bvn")
def verify_bvn(data: BvnIn, user: CurrentUser, db: DB):
    check_rate_limit(f"bvn:{user.id}", 5, 3600)
    flex.verify_bvn(db, user, data.bvn, data.date_of_birth)
    return service.eligibility(db, user)


@router.get("/profile/bank/link-session")
def bank_link_session(user: CurrentUser):
    """What the frontend needs to open the provider's bank-linking widget."""
    from app.integrations.bankdata import BANKS, get_bank_data_provider

    p = get_bank_data_provider()
    out = {"provider": p.name}
    if p.name == "mock":
        out.update(mock_personas=PERSONAS, mock_banks=BANKS,
                   notice="DEVELOPMENT ONLY: choose a test customer profile instead of logging in to a real bank.")
    elif p.name == "mono":
        out.update(public_key=settings.mono_public_key, customer={"name": user.full_name, "email": user.email},
                   notice="You'll be redirected to your bank's secure login to share read-only access to your transactions.")
    return out


@router.post("/profile/bank/connect")
def bank_connect(data: BankConnectIn, user: CurrentUser, db: DB):
    check_rate_limit(f"bank:{user.id}", 10, 3600)
    flex.connect_bank(db, user, data.code)
    return service.eligibility(db, user)


@router.post("/profile/employment")
def employment(data: EmploymentIn, user: CurrentUser, db: DB):
    check_rate_limit(f"employment:{user.id}", 10, 3600)
    _, link = flex.save_employment(db, user, data.model_dump())
    return {**service.eligibility(db, user), **_dev(link)}


@router.post("/profile/employment/verify-email")
def employment_verify(data: TokenIn, user: CurrentUser, db: DB):
    flex.verify_work_email(db, user, data.token)
    return service.eligibility(db, user)


@router.post("/profile/guarantor")
def guarantor(data: GuarantorIn, user: CurrentUser, db: DB):
    check_rate_limit(f"guarantor:{user.id}", 5, 86400)
    _, link = flex.add_guarantor(db, user, data.model_dump())
    return {**service.eligibility(db, user), **_dev(link)}


@router.delete("/profile/guarantor")
def cancel_guarantor(user: CurrentUser, db: DB):
    flex.cancel_guarantor(db, user)
    return service.eligibility(db, user)


@router.post("/profile/guarantor/resend")
def resend_guarantor(user: CurrentUser, db: DB):
    check_rate_limit(f"guarantor:{user.id}", 5, 86400)
    _, link = flex.resend_guarantor(db, user)
    return {**service.eligibility(db, user), **_dev(link)}


@router.get("/guarantor/{token}")
def guarantor_request(token: str, db: DB):
    """Public page data for the guarantor (they don't need a Goods.ng account)."""
    g = flex.guarantor_by_token(db, token)
    from app.models import User as U

    borrower = db.get(U, g.user_id)
    amount = g.amount_guaranteed if g.amount_guaranteed is not None else flex.guaranteed_amount(db, borrower)
    return {"guarantor_name": g.full_name, "borrower_name": borrower.full_name, "relationship": g.relationship_to_user,
            "status": g.status, "amount_guaranteed": f"{amount:.2f}", "expires_at": g.consent_expires_at}


@router.post("/guarantor/{token}")
def guarantor_respond(token: str, data: ConsentIn, request: Request, db: DB):
    check_rate_limit(f"guarantor-respond:{client_ip(request)}", 20, 3600)
    g = flex.guarantor_respond(db, token, data.agree, client_ip(request))
    return {"status": g.status}


@router.get("/applications")
def my_applications(user: CurrentUser, db: DB):
    rows = db.scalars(select(BnplApplication).where(BnplApplication.user_id == user.id)
                      .order_by(BnplApplication.created_at.desc()).limit(50)).all()
    return [service.application_out(a) for a in rows]


@router.get("/applications/{application_id}")
def get_application(application_id: uuid.UUID, user: CurrentUser, db: DB):
    return service.application_out(service.get_owned(db, user, application_id))


class AcceptIn(BaseModel):
    accept_terms: bool


@router.post("/applications/{application_id}/accept")
def accept(application_id: uuid.UUID, data: AcceptIn, request: Request, user: CurrentUser, db: DB):
    if not data.accept_terms:
        from app.core.errors import AppError

        raise AppError("You must accept the financing terms to continue", code="terms_not_accepted")
    pay = service.accept(db, user, application_id, client_ip(request))
    return {"payment_reference": pay.reference, "authorization_url": pay.authorization_url,
            "down_payment": f"{pay.amount:.2f}"}


@router.get("/agreements")
def my_agreements(user: CurrentUser, db: DB):
    rows = db.scalars(select(FinancingAgreement).join(BnplApplication).where(BnplApplication.user_id == user.id)
                      .order_by(FinancingAgreement.created_at.desc())).all()
    total_outstanding = sum((r.outstanding_balance for r in rows if r.status == "active"), Decimal("0"))
    return {"total_outstanding": f"{total_outstanding:.2f}", "agreements": [service.agreement_out(r) for r in rows]}


@router.post("/installments/{installment_id}/pay")
def pay_installment(installment_id: uuid.UUID, user: CurrentUser, db: DB):
    pay = service.pay_installment(db, user, installment_id)
    return {"payment_reference": pay.reference, "authorization_url": pay.authorization_url, "amount": f"{pay.amount:.2f}"}
