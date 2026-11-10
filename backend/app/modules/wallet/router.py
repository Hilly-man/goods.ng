import uuid
from decimal import Decimal

from fastapi import APIRouter, Header
from pydantic import BaseModel, Field

from app.core.cache import check_rate_limit
from app.core.deps import DB, CurrentSeller
from app.modules.wallet import service

router = APIRouter(tags=["wallet"])


class BankAccountIn(BaseModel):
    bank_code: str = Field(min_length=2, max_length=10)
    bank_name: str = Field(min_length=2, max_length=80)
    account_number: str = Field(min_length=10, max_length=20)
    is_default: bool = False


class PayoutIn(BaseModel):
    amount: Decimal = Field(gt=0)
    bank_account_id: uuid.UUID


@router.get("/seller/wallet")
def wallet(seller: CurrentSeller, db: DB):
    return {**service.summary(db, seller), "bank_accounts": service.list_bank_accounts(db, seller),
            "holds": service.holds_out(db, seller.id), "payouts": service.list_payouts(db, seller, limit=20)}


@router.get("/seller/bank-accounts")
def bank_accounts(seller: CurrentSeller, db: DB):
    return service.list_bank_accounts(db, seller)


@router.post("/seller/bank-accounts", status_code=201)
def add_bank_account(data: BankAccountIn, seller: CurrentSeller, db: DB):
    check_rate_limit(f"bank-account:{seller.id}", 10, 3600)
    return service.bank_account_out(service.add_bank_account(
        db, seller, bank_code=data.bank_code, bank_name=data.bank_name,
        account_number=data.account_number, is_default=data.is_default))


@router.delete("/seller/bank-accounts/{account_id}", status_code=204)
def delete_bank_account(account_id: uuid.UUID, seller: CurrentSeller, db: DB):
    service.remove_bank_account(db, seller, account_id)


@router.get("/seller/payouts")
def payouts(seller: CurrentSeller, db: DB):
    return service.list_payouts(db, seller)


@router.post("/seller/payouts", status_code=201)
def request_payout(data: PayoutIn, seller: CurrentSeller, db: DB,
                   idempotency_key: str | None = Header(None, max_length=80)):
    check_rate_limit(f"payout:{seller.id}", 5, 3600)
    payout = service.request_payout(db, seller, amount=data.amount, bank_account_id=data.bank_account_id,
                                    idempotency_key=idempotency_key)
    return service.payout_out(payout)


@router.post("/seller/payouts/{payout_id}/retry")
def retry_payout(payout_id: uuid.UUID, seller: CurrentSeller, db: DB):
    payout = service.retry_payout(db, payout_id)
    if payout.seller_id != seller.id:
        from app.core.errors import NotFound

        raise NotFound("Payout not found")
    return service.payout_out(payout)
