"""Double-entry ledger service.

Account scheme (NGN):
  asset:escrow_partner_holding        funds held for us by the licensed escrow partner
  liability:escrow_obligations        what we owe out of held funds (to seller or back to buyer)
  liability:seller_payable:<seller>   seller's released earnings awaiting payout by the partner
  revenue:platform_commission         commission on completed protected sales
  revenue:protection_fees             buyer protection fees on completed sales
  asset:subscription_receipts         subscription/promotion payments collected via provider
  revenue:subscriptions               premium seller subscription revenue

Posting is idempotent by key: re-posting the same key returns the existing transaction rather than
double-counting. Balance is enforced in Python here AND by a deferred DB constraint trigger.
"""

import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.models import LedgerAccount, LedgerEntry, LedgerTransaction
from app.models.enums import EntryDirection, LedgerAccountType

ESCROW_HOLDING = ("asset:escrow_partner_holding", "Escrow partner holding", LedgerAccountType.ASSET)
ESCROW_OBLIGATIONS = ("liability:escrow_obligations", "Escrow obligations", LedgerAccountType.LIABILITY)
COMMISSION = ("revenue:platform_commission", "Platform commission", LedgerAccountType.REVENUE)
PROTECTION_FEES = ("revenue:protection_fees", "Buyer protection fees", LedgerAccountType.REVENUE)
SUBSCRIPTION_RECEIPTS = ("asset:provider_receipts", "Provider receipts (non-escrow)", LedgerAccountType.ASSET)
FLEX_SELLER_SHARE = ("expense:flex_seller_share", "Goods Flex seller share", LedgerAccountType.EXPENSE)
SUBSCRIPTION_REVENUE = ("revenue:subscriptions", "Premium subscriptions", LedgerAccountType.REVENUE)
PROMOTION_REVENUE = ("revenue:promotions", "Listing promotions", LedgerAccountType.REVENUE)


def seller_payable(seller_id) -> tuple[str, str, LedgerAccountType]:
    return (f"liability:seller_payable:{seller_id}", f"Seller payable {seller_id}", LedgerAccountType.LIABILITY)


class LedgerError(Exception):
    pass


@dataclass
class Leg:
    account: tuple[str, str, LedgerAccountType]
    direction: EntryDirection
    amount: Decimal


def debit(account, amount) -> Leg:
    return Leg(account, EntryDirection.DEBIT, Decimal(amount))


def credit(account, amount) -> Leg:
    return Leg(account, EntryDirection.CREDIT, Decimal(amount))


def get_account(db: Session, spec) -> LedgerAccount:
    code, name, typ = spec
    db.execute(
        insert(LedgerAccount)
        .values(code=code, name=name, type=typ.value, currency="NGN", created_at=utcnow(),
                owner_ref=code.split(":")[2] if code.count(":") >= 2 else None, id=uuid.uuid4())
        .on_conflict_do_nothing(index_elements=["code"])
    )
    return db.execute(select(LedgerAccount).where(LedgerAccount.code == code)).scalar_one()


def post(db: Session, *, key: str, kind: str, description: str, legs: list[Leg], reference: str | None = None,
         meta: dict | None = None) -> LedgerTransaction:
    existing = db.execute(select(LedgerTransaction).where(LedgerTransaction.idempotency_key == key)).scalar_one_or_none()
    if existing:
        return existing
    legs = [lg for lg in legs if lg.amount > 0]
    debits = sum((lg.amount for lg in legs if lg.direction == EntryDirection.DEBIT), Decimal("0"))
    credits = sum((lg.amount for lg in legs if lg.direction == EntryDirection.CREDIT), Decimal("0"))
    if len(legs) < 2 or debits != credits:
        raise LedgerError(f"Unbalanced ledger transaction {key}: debits={debits} credits={credits}")
    now = utcnow()
    txn = LedgerTransaction(idempotency_key=key, kind=kind, description=description, reference=reference,
                            meta=meta or {}, created_at=now)
    db.add(txn)
    db.flush()
    for lg in legs:
        acct = get_account(db, lg.account)
        db.add(LedgerEntry(transaction_id=txn.id, account_id=acct.id, direction=lg.direction, amount=lg.amount,
                           created_at=now))
    db.flush()
    return txn


def balance(db: Session, code: str) -> Decimal:
    """Natural balance: debit-normal for assets/expenses, credit-normal for liabilities/revenue."""
    acct = db.execute(select(LedgerAccount).where(LedgerAccount.code == code)).scalar_one_or_none()
    if not acct:
        return Decimal("0.00")
    rows = db.execute(
        select(LedgerEntry.direction, func.coalesce(func.sum(LedgerEntry.amount), 0))
        .where(LedgerEntry.account_id == acct.id)
        .group_by(LedgerEntry.direction)
    ).all()
    sums = {d: Decimal(v) for d, v in rows}
    dr, cr = sums.get(EntryDirection.DEBIT, Decimal("0")), sums.get(EntryDirection.CREDIT, Decimal("0"))
    bal = dr - cr if acct.type in (LedgerAccountType.ASSET, LedgerAccountType.EXPENSE) else cr - dr
    return bal.quantize(Decimal("0.01"))


def trial_balance(db: Session) -> dict:
    rows = db.execute(
        select(LedgerEntry.direction, func.coalesce(func.sum(LedgerEntry.amount), 0)).group_by(LedgerEntry.direction)
    ).all()
    sums = {d: Decimal(v) for d, v in rows}
    dr, cr = sums.get(EntryDirection.DEBIT, Decimal("0")), sums.get(EntryDirection.CREDIT, Decimal("0"))
    return {"debits": dr, "credits": cr, "balanced": dr == cr}
