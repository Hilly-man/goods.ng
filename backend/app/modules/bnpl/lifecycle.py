"""Goods Flex lifecycle — the ONLY place application, agreement and instalment statuses change.

Read this file to understand Goods Flex. Every status change goes through `move_*`, which refuses any
transition not listed below (InvalidState), so a bug elsewhere can never put a plan into an impossible state.

    APPLICATION  submitted ─┬─> approved ──> accepted ──> active ──┬─> completed   (all instalments paid)
                            └─> declined     │             │       └─> defaulted ──┬─> active (caught up)
                                             │             │                       └─> completed
                   approved/accepted/active/defaulted ──> cancelled  (withdrawn, offer expired, order refunded)

    AGREEMENT    (created when the buyer accepts the lender's terms)
                 accepted ──> active ──┬─> completed
                                       ├─> defaulted ──> active | completed
                                       └─> cancelled            (order refunded before completion)

    INSTALMENT   scheduled ──┬─> paid
                             ├─> overdue ──> paid
                             └─> cancelled     (also overdue/failed ──> cancelled when the plan is cancelled)

Money rules (enforced in service.py):
* A payment is credited only after the payment provider confirms the exact amount and currency (payments/service.py).
* One open payment per instalment: asking to pay again reuses it, so double taps can't double-charge.
* Anything received beyond what an instalment needs (late duplicate, overpayment) is refunded automatically.
* A plan is "defaulted" once an instalment is 30+ days overdue; the customer can still pay it off.
"""

from app.core.errors import InvalidState
from app.core.time import utcnow
from app.models import BnplApplication, FinancingAgreement, Installment
from app.models.enums import BnplStatus as B
from app.models.enums import InstallmentStatus as I

DEFAULT_AFTER_DAYS = 30

APPLICATION: dict[B, set[B]] = {
    B.SUBMITTED: {B.APPROVED, B.DECLINED, B.CANCELLED},
    B.APPROVED: {B.ACCEPTED, B.CANCELLED},
    B.ACCEPTED: {B.ACTIVE, B.CANCELLED},
    B.ACTIVE: {B.COMPLETED, B.DEFAULTED, B.CANCELLED},
    B.DEFAULTED: {B.ACTIVE, B.COMPLETED, B.CANCELLED},
    B.DECLINED: set(),
    B.COMPLETED: set(),
    B.CANCELLED: set(),
}

AGREEMENT: dict[B, set[B]] = {
    B.ACCEPTED: {B.ACTIVE, B.CANCELLED},
    B.ACTIVE: {B.COMPLETED, B.DEFAULTED, B.CANCELLED},
    B.DEFAULTED: {B.ACTIVE, B.COMPLETED, B.CANCELLED},
    B.COMPLETED: set(),
    B.CANCELLED: set(),
}

INSTALMENT: dict[I, set[I]] = {
    I.SCHEDULED: {I.PAID, I.OVERDUE, I.CANCELLED},
    I.OVERDUE: {I.PAID, I.CANCELLED},
    I.FAILED: {I.PAID, I.OVERDUE, I.CANCELLED},
    I.PAID: set(),
    I.CANCELLED: set(),
}

PAYABLE_INSTALMENT = {I.SCHEDULED, I.OVERDUE, I.FAILED}
PAYABLE_PLAN = {B.ACTIVE, B.DEFAULTED}          # a defaulted customer must still be able to pay off
OPEN_APPLICATION = {B.APPROVED, B.ACCEPTED}      # not yet paid for — may be withdrawn / expired


def _move(kind: str, table: dict, obj, to) -> bool:
    """Returns False for a no-op (already in that state); raises on an illegal move."""
    frm = obj.status
    if frm == to:
        return False
    if to not in table.get(frm, set()):
        raise InvalidState(f"Goods Flex {kind} can't go from {getattr(frm, 'value', frm)} to {to.value}",
                           code="invalid_flex_transition")
    obj.status = to
    return True


def move_application(a: BnplApplication, to: B) -> bool:
    return _move("application", APPLICATION, a, to)


def move_agreement(ag: FinancingAgreement, to: B) -> bool:
    return _move("plan", AGREEMENT, ag, to)


def move_instalment(inst: Installment, to: I) -> bool:
    changed = _move("instalment", INSTALMENT, inst, to)
    if changed and to == I.PAID:
        inst.paid_at = utcnow()
    return changed


def move_plan(ag: FinancingAgreement, to: B) -> None:
    """Agreement and its application move together once the plan exists."""
    move_agreement(ag, to)
    move_application(ag.application, to)
