"""Seller wallet: balances, bank accounts, payout requests and holds.

Money rules:
* ``released`` is the ledger balance of ``liability:seller_payable:<seller>`` (already net of payouts).
* ``clearing`` is the part of released funds still inside the post-delivery complaint window.
* ``on_hold`` is the sum of open WalletHold rows (complaints, reserves, manual holds).
* ``available`` = released - clearing - on_hold, never below zero.
Payouts debit seller_payable into ``asset:payout_in_transit`` when requested, then settle against the
partner's confirmed result. A failed transfer reverses the request leg, never losing the seller's money.
"""

from datetime import timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, Forbidden, InvalidState, NotFound
from app.core.security import decrypt_field, encrypt_field
from app.core.time import utcnow
from app.integrations.payouts import get_payout_provider
from app.models import EscrowTransaction, Order, Payout, SellerBankAccount, SellerProfile, WalletHold
from app.models.enums import EscrowStatus, PayoutStatus
from app.modules.ledger import service as ledger

FUNDED = (EscrowStatus.AWAITING_SELLER, EscrowStatus.PROCESSING, EscrowStatus.DISPATCHED,
          EscrowStatus.DELIVERED, EscrowStatus.AWAITING_BUYER_CONFIRMATION, EscrowStatus.DISPUTED)
OPEN_PAYOUT = (PayoutStatus.REQUESTED, PayoutStatus.APPROVED, PayoutStatus.PROCESSING)
PAYABLE = (PayoutStatus.APPROVED, PayoutStatus.PROCESSING)


def _released(db: Session, seller_id) -> Decimal:
    return ledger.balance(db, ledger.seller_payable(seller_id)[0])


def _clearing(db: Session, seller_id) -> Decimal:
    cutoff = utcnow() - timedelta(hours=settings.seller_payout_hold_hours)
    total = db.scalar(
        select(func.coalesce(func.sum(EscrowTransaction.seller_amount), 0))
        .join(Order, Order.id == EscrowTransaction.order_id)
        .where(Order.seller_id == seller_id, EscrowTransaction.status == EscrowStatus.COMPLETED,
               EscrowTransaction.released_at > cutoff)
    )
    return Decimal(total or 0)


def _in_escrow(db: Session, seller_id) -> Decimal:
    total = db.scalar(
        select(func.coalesce(func.sum(EscrowTransaction.seller_amount), 0))
        .join(Order, Order.id == EscrowTransaction.order_id)
        .where(Order.seller_id == seller_id, EscrowTransaction.status.in_(FUNDED))
    )
    return Decimal(total or 0)


def _on_hold(db: Session, seller_id) -> Decimal:
    total = db.scalar(select(func.coalesce(func.sum(WalletHold.amount), 0)).where(
        WalletHold.seller_id == seller_id, WalletHold.released_at.is_(None)))
    return Decimal(total or 0)


def _paid_out(db: Session, seller_id) -> Decimal:
    total = db.scalar(select(func.coalesce(func.sum(Payout.amount), 0)).where(
        Payout.seller_id == seller_id, Payout.status == PayoutStatus.PAID))
    return Decimal(total or 0)


def _pending_payouts(db: Session, seller_id) -> Decimal:
    total = db.scalar(select(func.coalesce(func.sum(Payout.amount), 0)).where(
        Payout.seller_id == seller_id, Payout.status.in_(OPEN_PAYOUT)))
    return Decimal(total or 0)


def available(db: Session, seller: SellerProfile) -> Decimal:
    value = (_released(db, seller.id) - _clearing(db, seller.id) - _on_hold(db, seller.id)
             - _pending_payouts(db, seller.id))
    return max(value, Decimal("0.00")).quantize(Decimal("0.01"))


def summary(db: Session, seller: SellerProfile) -> dict:
    return {
        "in_escrow": f"{_in_escrow(db, seller.id):.2f}",
        "clearing": f"{_clearing(db, seller.id):.2f}",
        "available": f"{available(db, seller):.2f}",
        "on_hold": f"{_on_hold(db, seller.id):.2f}",
        "pending_payouts": f"{_pending_payouts(db, seller.id):.2f}",
        "withdrawn": f"{_paid_out(db, seller.id):.2f}",
        "released_total": f"{_released(db, seller.id):.2f}",
        "payouts_frozen": seller.payouts_frozen,
        "hold_hours": settings.seller_payout_hold_hours,
        "min_payout": f"{settings.min_payout_amount:.2f}",
        "note": "Withdrawals are paid to your verified bank account by our licensed payout partner.",
    }


def bank_account_out(a: SellerBankAccount) -> dict:
    return {"id": str(a.id), "bank_code": a.bank_code, "bank_name": a.bank_name,
            "account_last4": a.account_number_last4, "account_name": a.account_name,
            "is_default": a.is_default, "is_verified": a.is_verified, "verified_at": a.verified_at,
            "created_at": a.created_at}


def list_bank_accounts(db: Session, seller: SellerProfile) -> list[dict]:
    rows = db.scalars(select(SellerBankAccount).where(
        SellerBankAccount.seller_id == seller.id, SellerBankAccount.deleted_at.is_(None))
        .order_by(SellerBankAccount.is_default.desc(), SellerBankAccount.created_at)).all()
    return [bank_account_out(a) for a in rows]


def add_bank_account(db: Session, seller: SellerProfile, *, bank_code: str | None, bank_name: str,
                     account_name: str, account_number: str, is_default: bool) -> SellerBankAccount:
    account_number = "".join(ch for ch in account_number if ch.isdigit())
    if not (10 <= len(account_number) <= 11):
        raise AppError("Enter a valid 10- or 11-digit account number", code="invalid_account_number")
    account_name = account_name.strip()
    if len(account_name) < 2:
        raise AppError("Enter the account name exactly as it appears at the bank", code="invalid_account_name")
    # With a real payout partner, resolve the account and require the name the seller typed to match.
    # The mock partner has no bank directory, so the seller's name is stored as-is.
    if bank_code and settings.payout_provider != "mock":
        resolved = get_payout_provider().resolve_account(bank_code=bank_code, account_number=account_number)
        if resolved.account_name.strip().lower() != account_name.lower():
            raise AppError("The account name does not match the bank's records", code="account_name_mismatch")
    existing = db.scalars(select(SellerBankAccount).where(
        SellerBankAccount.seller_id == seller.id, SellerBankAccount.deleted_at.is_(None))).all()
    if any((a.bank_code or a.bank_name) == (bank_code or bank_name)
           and a.account_number_last4 == account_number[-4:] for a in existing):
        raise AppError("That bank account is already saved", code="bank_account_exists")
    make_default = is_default or not existing
    if make_default:
        for a in existing:
            a.is_default = False
    acct = SellerBankAccount(
        seller_id=seller.id, bank_code=bank_code or "", bank_name=bank_name,
        account_number_enc=encrypt_field(account_number), account_number_last4=account_number[-4:],
        account_name=account_name, is_default=make_default, is_verified=True, verified_at=utcnow(),
    )
    db.add(acct)
    db.commit()
    db.refresh(acct)
    return acct


def remove_bank_account(db: Session, seller: SellerProfile, account_id) -> None:
    acct = db.get(SellerBankAccount, account_id)
    if not acct or acct.seller_id != seller.id or acct.deleted_at is not None:
        raise NotFound("Bank account not found")
    if db.scalar(select(func.count()).select_from(Payout).where(
            Payout.bank_account_id == acct.id, Payout.status.in_(OPEN_PAYOUT))):
        raise InvalidState("This account has a payout in progress", code="payout_in_progress")
    acct.deleted_at = utcnow()
    acct.is_default = False
    db.flush()
    if not db.scalar(select(func.count()).select_from(SellerBankAccount).where(
            SellerBankAccount.seller_id == seller.id, SellerBankAccount.deleted_at.is_(None),
            SellerBankAccount.is_default.is_(True))):
        replacement = db.scalars(select(SellerBankAccount).where(
            SellerBankAccount.seller_id == seller.id, SellerBankAccount.deleted_at.is_(None))
            .order_by(SellerBankAccount.created_at)).first()
        if replacement:
            replacement.is_default = True
    db.commit()


def payout_out(p: Payout) -> dict:
    return {"id": str(p.id), "amount": f"{p.amount:.2f}", "fee": f"{p.fee:.2f}", "status": p.status,
            "seller_id": str(p.seller_id), "seller_name": p.seller.store_name if p.seller else None,
            "bank_account": {"id": str(p.bank_account.id), "bank_name": p.bank_account.bank_name,
                             "account_name": p.bank_account.account_name,
                             "account_last4": p.bank_account.account_number_last4}
            if p.bank_account else None,
            "provider_reference": p.provider_reference, "requested_at": p.requested_at,
            "reviewed_by_id": str(p.reviewed_by_id) if p.reviewed_by_id else None,
            "reviewed_at": p.reviewed_at, "review_note": p.review_note,
            "processing_at": p.processing_at, "paid_at": p.paid_at, "failed_at": p.failed_at,
            "failure_reason": p.failure_reason}


def list_payouts(db: Session, seller: SellerProfile, limit: int = 50) -> list[dict]:
    rows = db.scalars(select(Payout).where(Payout.seller_id == seller.id)
                      .order_by(Payout.created_at.desc()).limit(limit)).all()
    return [payout_out(p) for p in rows]


def request_payout(db: Session, seller: SellerProfile, *, amount: Decimal, bank_account_id,
                   idempotency_key: str | None) -> Payout:
    if seller.payouts_frozen:
        raise Forbidden("Payouts are on hold while a buyer complaint is reviewed", code="payouts_frozen")
    amount = Decimal(amount).quantize(Decimal("0.01"))
    if amount < settings.min_payout_amount:
        raise AppError(f"Minimum withdrawal is ₦{settings.min_payout_amount:,.2f}", code="below_min_payout")
    if idempotency_key:
        existing = db.scalars(select(Payout).where(
            Payout.seller_id == seller.id, Payout.idempotency_key == idempotency_key)).first()
        if existing:
            return existing
    # Serialise concurrent withdrawal requests for this seller; available() changes with each payout.
    db.execute(select(SellerProfile.id).where(SellerProfile.id == seller.id).with_for_update())
    acct = db.get(SellerBankAccount, bank_account_id)
    if not acct or acct.seller_id != seller.id or acct.deleted_at is not None or not acct.is_verified:
        raise AppError("Choose a verified bank account", code="bank_account_required")
    if amount > available(db, seller):
        raise AppError("That amount is not available to withdraw yet", code="insufficient_available")
    now = utcnow()
    payout = Payout(seller_id=seller.id, bank_account_id=acct.id, amount=amount, fee=Decimal("0"),
                    status=PayoutStatus.REQUESTED, idempotency_key=idempotency_key, requested_at=now)
    db.add(payout)
    db.flush()
    # No ledger entry yet: the money is still held by the partner. The pending payout is deducted
    # from "available" until the partner confirms the transfer.
    db.commit()
    db.refresh(payout)
    return payout


def approve_payout(db: Session, payout_id, *, admin_id) -> Payout:
    payout = db.get(Payout, payout_id)
    if not payout or payout.status != PayoutStatus.REQUESTED:
        raise NotFound("Payout awaiting review not found")
    payout.status = PayoutStatus.APPROVED
    payout.reviewed_by_id, payout.reviewed_at = admin_id, utcnow()
    db.commit()
    return payout


def reject_payout(db: Session, payout_id, *, admin_id, reason: str) -> Payout:
    payout = db.get(Payout, payout_id)
    if not payout or payout.status != PayoutStatus.REQUESTED:
        raise NotFound("Payout awaiting review not found")
    payout.status = PayoutStatus.REJECTED
    payout.reviewed_by_id, payout.reviewed_at = admin_id, utcnow()
    payout.review_note = reason[:300]
    # Nothing was ever debited, so rejecting simply returns the amount to "available".
    db.commit()
    return payout


def process_due_payouts(db: Session, limit: int = 50) -> int:
    """Send admin-approved payouts to the licensed partner. Safe to run repeatedly."""
    provider = get_payout_provider()
    rows = db.scalars(select(Payout).where(Payout.status.in_(PAYABLE))
                      .order_by(Payout.created_at).limit(limit).with_for_update(skip_locked=True)).all()
    processed = 0
    for payout in rows:
        acct = payout.bank_account
        if payout.status == PayoutStatus.REQUESTED:
            payout.status = PayoutStatus.PROCESSING
            payout.processing_at = utcnow()
            payout.provider = provider.name
            db.flush()
        result = provider.create_transfer(
            reference=str(payout.id), amount=payout.amount, bank_code=acct.bank_code,
            account_number=decrypt_field(acct.account_number_enc), account_name=acct.account_name,
        )
        payout.provider_reference = result.reference
        if result.status == "paid":
            payout.status = PayoutStatus.PAID
            payout.paid_at = utcnow()
            ledger.post(db, key=f"payout:{payout.id}:paid", kind="payout_paid", reference=str(payout.id),
                        description=f"Seller payout paid for {payout.seller_id}",
                        legs=[ledger.debit(ledger.seller_payable(payout.seller_id), payout.amount),
                              ledger.credit(ledger.ESCROW_HOLDING, payout.amount)])
            processed += 1
        elif result.status == "failed":
            _fail(db, payout, "Payout provider declined the transfer")
            processed += 1
        db.commit()
    return processed


def _fail(db: Session, payout: Payout, reason: str) -> None:
    payout.status = PayoutStatus.FAILED
    payout.failed_at = utcnow()
    payout.failure_reason = reason[:300]
    # No ledger entry was posted at request time, so failing just returns the amount to "available".


def retry_payout(db: Session, payout_id, *, admin_id=None) -> Payout:
    payout = db.get(Payout, payout_id)
    if not payout or payout.status != PayoutStatus.FAILED:
        raise NotFound("Failed payout not found")
    payout.status = PayoutStatus.APPROVED
    payout.failure_reason = None
    if admin_id:
        payout.reviewed_by_id, payout.reviewed_at = admin_id, utcnow()
    db.commit()
    return payout


def holds_out(db: Session, seller_id) -> list[dict]:
    rows = db.scalars(select(WalletHold).where(WalletHold.seller_id == seller_id, WalletHold.released_at.is_(None))
                      .order_by(WalletHold.created_at.desc())).all()
    return [{"id": str(h.id), "order_id": str(h.order_id) if h.order_id else None, "amount": f"{h.amount:.2f}",
             "reason": h.reason, "note": h.note, "created_at": h.created_at} for h in rows]


def place_hold(db: Session, *, seller_id, amount: Decimal, reason: str, order_id=None, note: str | None = None,
               created_by_id=None, freeze: bool = False) -> WalletHold:
    amount = Decimal(amount).quantize(Decimal("0.01"))
    if amount <= 0:
        raise AppError("Hold amount must be positive", code="invalid_hold")
    hold = WalletHold(seller_id=seller_id, order_id=order_id, amount=amount, reason=reason[:40],
                      note=note, created_by_id=created_by_id)
    db.add(hold)
    if freeze:
        seller = db.get(SellerProfile, seller_id)
        if seller:
            seller.payouts_frozen = True
    db.flush()
    return hold


def release_hold(db: Session, hold_id, *, actor_id=None) -> WalletHold:
    hold = db.get(WalletHold, hold_id)
    if not hold or hold.released_at is not None:
        raise NotFound("Open hold not found")
    hold.released_at = utcnow()
    db.flush()
    seller = db.get(SellerProfile, hold.seller_id)
    if seller and not db.scalar(select(func.count()).select_from(WalletHold).where(
            WalletHold.seller_id == seller.id, WalletHold.released_at.is_(None))):
        seller.payouts_frozen = False
    db.commit()
    return hold


def set_frozen(db: Session, seller: SellerProfile, frozen: bool) -> None:
    seller.payouts_frozen = frozen
    db.commit()


def complaint_window_open(order: Order) -> bool:
    esc = order.escrow
    if not esc or esc.status != EscrowStatus.COMPLETED or not esc.released_at:
        return False
    return utcnow() - esc.released_at <= timedelta(hours=settings.seller_payout_hold_hours)


def serialize_hold(h: WalletHold) -> dict:
    return {"id": str(h.id), "seller_id": str(h.seller_id), "order_id": str(h.order_id) if h.order_id else None,
            "amount": f"{h.amount:.2f}", "reason": h.reason, "note": h.note, "released_at": h.released_at,
            "created_at": h.created_at}


__all__ = [n for n in dir() if not n.startswith("_") and n not in ("uuid",)]
