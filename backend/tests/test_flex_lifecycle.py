"""Goods Flex + escrow engine guarantees: legal transitions only, no lost or double-counted money."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.core.errors import InvalidState
from app.models import BnplApplication, EscrowTransaction, Installment, Order, Payment, Repayment, User
from app.models.enums import BnplStatus, InstallmentStatus, PaymentPurpose
from app.modules.bnpl import lifecycle as life
from app.modules.bnpl.service import mark_overdue_and_remind
from app.modules.orders import escrow
from app.modules.payments import service as payments
from tests.conftest import simulate_payment
from tests.test_flex import apply, flex_product, setup_flex


def a_id(db, inst):
    from app.models import FinancingAgreement
    return db.get(FinancingAgreement, inst.agreement_id).application_id


def _active_plan(make_user, make_seller, make_product):
    seller, buyer = make_seller(), make_user()
    setup_flex(buyer)
    a = apply(buyer, flex_product(make_product, seller)).json()
    pay = buyer.post(f"/bnpl/applications/{a['id']}/accept", {"accept_terms": True}).json()
    simulate_payment(buyer, pay["payment_reference"])
    ag = buyer.get("/bnpl/agreements").json()["agreements"][0]
    assert ag["status"] == "active"
    return buyer, a, ag


def test_double_tap_on_pay_reuses_the_open_payment(make_user, make_seller, make_product):
    buyer, _, ag = _active_plan(make_user, make_seller, make_product)
    inst = ag["installments"][0]["id"]
    r1 = buyer.post(f"/bnpl/installments/{inst}/pay").json()
    r2 = buyer.post(f"/bnpl/installments/{inst}/pay").json()
    assert r1["payment_reference"] == r2["payment_reference"]


def test_duplicate_payment_for_a_paid_instalment_is_refunded_not_kept(db, make_user, make_seller, make_product):
    buyer, _, ag = _active_plan(make_user, make_seller, make_product)
    inst_id = ag["installments"][0]["id"]
    first = buyer.post(f"/bnpl/installments/{inst_id}/pay").json()["payment_reference"]
    # A second charge created separately (e.g. another device) before the first completed:
    inst = db.get(Installment, inst_id)
    dup = payments.create_payment(db, user=db.get(User, buyer.user["id"]), purpose=PaymentPurpose.BNPL_INSTALLMENT,
                                  amount=inst.amount, installment_id=inst.id, bnpl_application_id=a_id(db, inst),
                                  callback_path="/flex")
    db.commit()
    simulate_payment(buyer, first)
    simulate_payment(buyer, dup.reference)
    db.expire_all()
    inst = db.get(Installment, inst_id)
    assert inst.status == InstallmentStatus.PAID and inst.amount_paid == inst.amount  # credited once
    d = db.query(Payment).filter_by(reference=dup.reference).one()
    assert d.amount_refunded == d.amount, "the duplicate charge must be refunded in full"
    assert db.query(Repayment).filter_by(payment_id=d.id, status="refunded").count() == 1


def test_defaulted_customer_can_pay_off_and_return_to_good_standing(db, make_user, make_seller, make_product):
    buyer, a, ag = _active_plan(make_user, make_seller, make_product)
    first = db.query(Installment).filter_by(agreement_id=ag["id"], sequence=1).one()
    first.due_date = date.today() - timedelta(days=45)
    db.commit()
    mark_overdue_and_remind(db)
    assert buyer.get("/bnpl/agreements").json()["agreements"][0]["status"] == "defaulted"
    r = buyer.post(f"/bnpl/installments/{first.id}/pay")
    assert r.status_code == 200, r.text  # defaulted plans must still accept payment
    simulate_payment(buyer, r.json()["payment_reference"])
    assert buyer.get("/bnpl/agreements").json()["agreements"][0]["status"] == "active"


def test_overdue_job_never_touches_a_paid_instalment(db, make_user, make_seller, make_product):
    buyer, _, ag = _active_plan(make_user, make_seller, make_product)
    inst = db.query(Installment).filter_by(agreement_id=ag["id"], sequence=1).one()
    simulate_payment(buyer, buyer.post(f"/bnpl/installments/{inst.id}/pay").json()["payment_reference"])
    db.expire_all()
    inst = db.get(Installment, inst.id)
    inst.due_date = date.today() - timedelta(days=5)
    db.commit()
    mark_overdue_and_remind(db)
    db.expire_all()
    assert db.get(Installment, inst.id).status == InstallmentStatus.PAID


def test_illegal_flex_transitions_are_rejected():
    a = BnplApplication(status=BnplStatus.DECLINED)
    with pytest.raises(InvalidState):
        life.move_application(a, BnplStatus.ACTIVE)
    i = Installment(status=InstallmentStatus.PAID, amount=Decimal("1"), amount_paid=Decimal("1"))
    with pytest.raises(InvalidState):
        life.move_instalment(i, InstallmentStatus.OVERDUE)  # paid stays paid
    assert life.move_application(BnplApplication(status=BnplStatus.APPROVED), BnplStatus.APPROVED) is False  # no-op


def test_every_flex_status_is_covered_by_the_lifecycle_tables():
    assert set(life.APPLICATION) == set(BnplStatus)
    assert set(life.INSTALMENT) == set(InstallmentStatus)


def test_escrow_refuses_to_change_status_without_a_row_lock(db, paid_order):
    _, _, _, order = paid_order()
    o = db.get(Order, order["id"])
    esc = db.query(EscrowTransaction).filter_by(order_id=o.id).one()
    with pytest.raises(RuntimeError, match="without escrow.lock"):
        escrow.transition(db, o, esc, escrow.S.PROCESSING)
    db.rollback()
    o, esc = escrow.lock(db, order["id"])
    escrow.transition(db, o, esc, escrow.S.PROCESSING)  # fine once locked
    db.rollback()


def test_escrow_refuses_to_release_mismatched_money(db, paid_order):
    _, _, _, order = paid_order()
    o, esc = escrow.lock(db, order["id"])
    esc.seller_amount += Decimal("1")  # tampered split
    with pytest.raises(InvalidState):
        escrow.release(db, o, esc)
    db.rollback()


def test_every_escrow_status_is_in_the_transition_table():
    assert set(escrow.ALLOWED) == set(escrow.S)
