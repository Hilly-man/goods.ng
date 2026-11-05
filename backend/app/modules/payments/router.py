from fastapi import APIRouter, Request

from app.core.deps import DB, CurrentUser
from app.core.errors import NotFound
from app.models import Payment
from app.modules.payments import service

router = APIRouter(prefix="/payments", tags=["payments"])


def payment_out(p: Payment) -> dict:
    # Internal provider payloads are never exposed.
    return {"reference": p.reference, "status": p.status, "purpose": p.purpose, "amount": f"{p.amount:.2f}",
            "currency": p.currency, "order_id": str(p.order_id) if p.order_id else None,
            "authorization_url": p.authorization_url if p.status == "initialized" else None,
            "verified_at": p.verified_at, "created_at": p.created_at}


@router.get("/{reference}")
def get_payment(reference: str, user: CurrentUser, db: DB):
    p = db.query(Payment).filter_by(reference=reference).one_or_none()
    if not p or (p.user_id != user.id and not user.is_admin):
        raise NotFound("Payment not found")
    return payment_out(p)


@router.post("/{reference}/verify")
def verify_payment(reference: str, user: CurrentUser, db: DB):
    """Called after the provider redirect. Triggers a server-side check; never trusts the client."""
    p = db.query(Payment).filter_by(reference=reference).one_or_none()
    if not p or (p.user_id != user.id and not user.is_admin):
        raise NotFound("Payment not found")
    return payment_out(service.confirm_payment(db, reference))


@router.post("/webhooks/{provider}/webhook", include_in_schema=False)
async def webhook(provider: str, request: Request, db: DB):
    if provider not in ("mock", "paystack", "flutterwave"):
        raise NotFound("Unknown provider")
    body = await request.body()
    headers = {k.lower(): v for k, v in request.headers.items()}
    return service.handle_webhook(db, provider, body, headers)
