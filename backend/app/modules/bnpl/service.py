"""Goods Flex (BNPL). Goods.ng facilitates; the licensed lending partner decides and lends.

Flow: apply (order created & stock reserved, partner decides) -> buyer reviews partner terms ->
accepts -> pays down payment -> partner disburses financed amount to the escrow partner -> order is
funded and proceeds through the normal protected-checkout lifecycle. Instalments are collected on
behalf of the lending partner.
"""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, Forbidden, InvalidState, NotFound
from app.core.time import utcnow
from app.integrations.bnpl import get_financing_provider
from app.models import (
    BnplApplication,
    FinancingAgreement,
    Installment,
    LedgerAccount,
    LedgerEntry,
    LedgerTransaction,
    Order,
    Payment,
    Product,
    Repayment,
    SellerProfile,
    User,
    WalletHold,
)
from app.models.enums import BnplStatus, EntryDirection, InstallmentStatus, PaymentMethod, PaymentPurpose
from app.modules.bnpl import lifecycle as life
from app.modules.ledger import service as ledger
from app.modules.notifications.service import notify
from app.modules.orders import escrow
from app.modules.orders import service as orders
from app.modules.payments import service as payments


def eligibility(db: Session, user: User) -> dict:
    from app.modules.bnpl import flex

    return flex_status(db, user, flex)


def flex_status(db: Session, user: User, flex) -> dict:
    info = flex.credit_limit(db, user)
    running = flex.running_plan(db, user.id)
    a = info["assessment"]
    prof = flex.profile(db, user)
    g = flex.active_guarantor(db, user.id)
    p = get_financing_provider()
    r = flex.rules(db)
    db.commit()
    return {
        "credit_limit": f"{info['limit']:.2f}",
        "available_to_spend": "0.00" if running else f"{info['limit']:.2f}",
        "binding_cap": info["binding_cap"],
        "caps": {k: f"{v:.2f}" for k, v in info["caps"].items()},
        "tips": info["tips"],
        "steps": info["steps"],
        "completed_plans": info["completed_plans"],
        "running_plan": {"application_id": str(running.id), "status": running.status,
                         "order_id": str(running.order_id) if running.order_id else None} if running else None,
        "can_apply": running is None and info["limit"] > 0,
        "profile": {
            "bvn_last4": prof.bvn_last4, "bvn_verified_at": prof.bvn_verified_at, "bvn_phone_match": prof.bvn_phone_match,
            "employment_type": prof.employment_type, "employer_name": prof.employer_name, "job_title": prof.job_title,
            "work_email": prof.work_email, "cac_number": prof.cac_number,
            "employment_verified_at": prof.employment_verified_at, "employment_method": prof.employment_method,
            "employment_pending": bool(prof.employment_type and not prof.employment_verified_at),
        },
        "guarantor": {"full_name": g.full_name, "phone": f"••••{g.phone[-4:]}", "relationship": g.relationship_to_user,
                      "status": g.status, "consented_at": g.consented_at,
                      "amount_guaranteed": f"{flex.guaranteed_amount(db, user):.2f}"} if g else None,
        "assessment": {
            "id": str(a.id), "created_at": a.created_at, "expires_at": a.expires_at, "months_analysed": a.months_analysed,
            "monthly_income": f"{a.monthly_income:.2f}", "income_source": a.income_source,
            "monthly_debt": f"{a.monthly_debt:.2f}", "affordable_instalment": f"{a.affordable_instalment:.2f}",
            "statement_limit": f"{a.statement_limit:.2f}", "score": a.score,
            "reasons": a.metrics.get("reasons", []), "monthly_inflows": a.metrics.get("monthly_inflows", []),
            "bank": {"name": a.bank_connection.bank_name, "account_last4": a.bank_connection.account_number_last4},
        } if a else None,
        "rules": {"tier1_max": str(r["tier1_max"]), "tier2_max": str(r["tier2_max"]), "lender_max": str(r["lender_max"]),
                  "max_dti": str(r["max_dti"])},
        "min_amount": f"{p.min_amount:.2f}", "tenors": list(p.tenors), "provider": p.name,
        "disclosure": "Goods Flex financing is provided by a licensed lending partner, subject to approval. "
                      "Your limit is calculated from your bank statement and verification; charges are shown before you accept.",
    }


def _has_overdue(db, user) -> bool:
    return db.scalar(select(Installment.id).join(FinancingAgreement).join(BnplApplication).where(
        BnplApplication.user_id == user.id, Installment.status == InstallmentStatus.OVERDUE).limit(1)) is not None


def quote(db: Session, product: Product, amount: Decimal) -> list[dict]:
    if not product.bnpl_enabled:
        return []
    return [o.as_dict() for o in get_financing_provider().quote(amount, date.today())]


def apply(db: Session, user: User, *, product_id, quantity, negotiation_id, delivery_index, address, note,
          tenor_months: int, idempotency_key: str | None) -> BnplApplication:
    from app.core.deps import ensure_customer

    ensure_customer(user)
    from sqlalchemy.exc import IntegrityError

    from app.modules.bnpl import flex

    # Idempotent retry of the same checkout attempt → return the existing application.
    if idempotency_key:
        prev = db.scalars(select(BnplApplication).join(Order, Order.id == BnplApplication.order_id).where(
            Order.buyer_id == user.id, Order.idempotency_key == idempotency_key)).first()
        if prev:
            return prev
    if _has_overdue(db, user):
        raise AppError("Please clear overdue Goods Flex instalments before applying again", code="bnpl_overdue")
    product = db.get(Product, product_id)
    if not product:
        from app.core.errors import NotFound

        raise NotFound("Listing not found")
    if not product.bnpl_enabled:
        raise AppError("Goods Flex is not available for this listing", code="bnpl_unavailable")
    q = orders.price_checkout(db, user, product, quantity, negotiation_id, delivery_index)
    info = flex.ensure_can_apply(db, user, q["total"])  # one running plan + credit limit
    assessment = info["assessment"]
    order, _ = orders.create_checkout(db, user, product_id=product_id, quantity=quantity,
                                      negotiation_id=negotiation_id, delivery_index=delivery_index, address=address,
                                      note=note, idempotency_key=idempotency_key, payment_method=PaymentMethod.BNPL)
    prof = flex.profile(db, user)
    provider = get_financing_provider()
    decision = provider.apply(
        applicant={"user_id": str(user.id), "email": user.email, "phone": user.phone,
                   "phone_verified": user.phone_verified, "bvn_verified": prof.bvn_verified_at is not None,
                   "monthly_income": str(assessment.monthly_income), "monthly_debt": str(assessment.monthly_debt),
                   "income_source": assessment.income_source, "goodsng_credit_limit": str(info["limit"]),
                   "goodsng_score": assessment.score, "employment_type": prof.employment_type,
                   "employment_verified": prof.employment_verified_at is not None},
        amount=order.total, tenor_months=tenor_months, start=date.today(),
    )
    app_ = BnplApplication(
        user_id=user.id, product_id=product_id, order_id=order.id, negotiation_id=negotiation_id,
        provider=provider.name, provider_application_ref=decision.application_ref,
        credit_decision_ref=decision.decision_ref, purchase_amount=order.total, tenor_months=tenor_months,
        monthly_income_declared=prof.monthly_income_declared, employment_status=prof.employment_type,
        # Created directly in the lender's decided state (submitted -> approved/declined happens in one call).
        status=BnplStatus.APPROVED if decision.approved else BnplStatus.DECLINED,
        decline_reason=decision.reason, offer_terms=decision.option.as_dict() if decision.option else {},
        offer_expires_at=utcnow() + timedelta(hours=24) if decision.approved else None,
        assessment_id=assessment.id, credit_limit_at_application=info["limit"],
    )
    db.add(app_)
    if not decision.approved:
        o, esc = escrow.lock(db, order.id)
        orders.cancel_unpaid(db, o, esc, reason="Goods Flex application declined")
    notify(db, user.id, "bnpl_decision", "Goods Flex decision",
           "Your Goods Flex application was approved. Review and accept the terms to continue."
           if decision.approved else f"Your Goods Flex application was not approved: {decision.reason}",
           link=f"/flex/applications/{app_.id}" if decision.approved else None)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        if flex.is_running_conflict(e):
            raise AppError("You already have a Goods Flex plan running.", code="bnpl_plan_running", status_code=409) from e
        raise
    return app_


def release_application(db: Session, a: BnplApplication, reason: str) -> None:
    """Cancel an approved/accepted application that never got funded, and its unpaid order (frees the plan slot)."""
    if a.status not in life.OPEN_APPLICATION:
        return
    order = db.get(Order, a.order_id) if a.order_id else None
    if order and order.status == "pending_payment":
        o, esc = escrow.lock(db, order.id)
        orders.cancel_unpaid(db, o, esc, reason=reason)
    if order:
        cancel_financing_for_order(db, order, reason)
    life.move_application(a, BnplStatus.CANCELLED)
    db.flush()


def withdraw(db: Session, user: User, application_id) -> BnplApplication:
    a = db.query(BnplApplication).filter_by(id=application_id).with_for_update().one_or_none()
    if not a or a.user_id != user.id:
        from app.core.errors import NotFound

        raise NotFound("Application not found")
    if a.status not in life.OPEN_APPLICATION:
        raise AppError("Only applications that haven't been paid for can be withdrawn", code="cannot_withdraw")
    release_application(db, a, "Withdrawn by customer")
    db.commit()
    return a


def get_owned(db: Session, user: User, application_id) -> BnplApplication:
    a = db.get(BnplApplication, application_id)
    if not a or a.user_id != user.id:
        raise NotFound("Application not found")
    return a


def accept(db: Session, user: User, application_id, ip: str) -> Payment:
    a = db.query(BnplApplication).filter_by(id=application_id).with_for_update().one_or_none()
    if not a or a.user_id != user.id:
        raise NotFound("Application not found")
    if a.status == BnplStatus.ACCEPTED:
        pay = db.scalars(select(Payment).where(Payment.bnpl_application_id == a.id,
                                               Payment.purpose == PaymentPurpose.BNPL_DOWN_PAYMENT)
                         .order_by(Payment.created_at.desc())).first()
        if pay and pay.status == "initialized":
            return pay
    if a.status != BnplStatus.APPROVED:
        raise InvalidState("This application cannot be accepted", code="bnpl_not_approved")
    if a.offer_expires_at and a.offer_expires_at < utcnow():
        raise InvalidState("This financing offer has expired", code="bnpl_offer_expired")
    order = db.get(Order, a.order_id)
    if order.status != "pending_payment":
        raise InvalidState("The order for this application is no longer open")
    t = a.offer_terms
    agreement_ref = get_financing_provider().accept(application_ref=a.provider_application_ref)
    down = Decimal(t["down_payment"])
    ag = FinancingAgreement(
        application_id=a.id, provider_agreement_ref=agreement_ref, purchase_amount=a.purchase_amount,
        down_payment=down, financed_amount=Decimal(t["financed_amount"]), financing_charge=Decimal(t["financing_charge"]),
        total_payable=Decimal(t["total_payable"]), tenor_months=a.tenor_months, terms_snapshot=t, accepted_at=utcnow(),
        accepted_ip=ip, outstanding_balance=Decimal(t["financed_amount"]) + Decimal(t["financing_charge"]),
        status=BnplStatus.ACCEPTED,
    )
    db.add(ag)
    db.flush()
    for s in t["schedule"]:
        db.add(Installment(agreement_id=ag.id, sequence=s["sequence"], due_date=date.fromisoformat(s["due_date"]),
                           amount=Decimal(s["amount"])))
    life.move_application(a, BnplStatus.ACCEPTED)
    pay = payments.create_payment(db, user=user, purpose=PaymentPurpose.BNPL_DOWN_PAYMENT, amount=down,
                                  order_id=order.id, bnpl_application_id=a.id,
                                  callback_path=f"/orders/{order.id}/payment", metadata={"order": order.order_number})
    db.commit()
    return pay


@payments.on_success(PaymentPurpose.BNPL_DOWN_PAYMENT)
def _down_paid(db: Session, payment: Payment) -> None:
    a = db.query(BnplApplication).filter_by(id=payment.bnpl_application_id).with_for_update().one()
    ag = a.agreement
    if a.status != BnplStatus.ACCEPTED or not ag or payment.amount != ag.down_payment or payment.user_id != a.user_id:
        # Late/duplicate/mismatched down payment (e.g. the offer was withdrawn meanwhile): never keep the money.
        _refund_unapplied(db, payment, payment.amount, "Goods Flex down payment could not be applied")
        return
    # Partner disburses the financed amount to the escrow partner (mock: immediate).
    life.move_plan(ag, BnplStatus.ACTIVE)
    order, esc = escrow.lock(db, a.order_id)
    orders.on_order_funded(db, order, esc, payment)
    seller = db.get(SellerProfile, order.seller_id)
    notify(db, seller.user_id, "new_order", "Goods Flex order funded",
           f"Order {order.order_number} is fully funded via Goods Flex.", link=f"/seller/orders/{order.id}")


def seller_share_rate(db: Session) -> Decimal:
    from app.modules.bnpl import flex

    return Decimal(str(flex.rules(db)["seller_share_rate"]))


def schedule_seller_holds(db: Session, order: Order, esc) -> None:
    """For a Goods Flex order, hold the financed principal portion of the seller's earnings until
    each instalment is paid. The down-payment share stays available."""
    if order.payment_method != PaymentMethod.BNPL:
        return
    a = db.query(BnplApplication).filter_by(order_id=order.id).first()
    ag = a.agreement if a else None
    if not ag or not ag.installments:
        return
    principal = ag.down_payment + ag.financed_amount
    if principal <= 0:
        return
    hold_total = (esc.seller_amount * ag.financed_amount / principal).quantize(Decimal("0.01"))
    installments = sorted(ag.installments, key=lambda i: i.sequence)
    existing = {h.installment_id for h in db.query(WalletHold).filter_by(order_id=order.id).all()}
    if any(i.id in existing for i in installments):
        return  # already scheduled
    share = (hold_total / len(installments)).quantize(Decimal("0.01"))
    allocated = Decimal("0.00")
    for i, inst in enumerate(installments):
        amount = hold_total - allocated if i == len(installments) - 1 else share
        allocated += amount
        if amount <= 0 or inst.status in (InstallmentStatus.PAID, InstallmentStatus.CANCELLED):
            continue
        db.add(WalletHold(seller_id=order.seller_id, order_id=order.id, installment_id=inst.id, amount=amount,
                          reason="bnpl_instalment",
                          note=f"Goods Flex principal held until instalment {inst.sequence} is paid"))


def _release_bnpl_instalment(db: Session, inst: Installment, ag: FinancingAgreement) -> None:
    """Release the principal hold for a paid instalment and credit the seller's share of that month's charge."""
    hold = (db.query(WalletHold).filter_by(installment_id=inst.id, released_at=None)
            .with_for_update().first())
    released_principal = Decimal("0.00")
    if hold:
        hold.released_at = utcnow()
        released_principal = hold.amount

    monthly_interest = (ag.financing_charge / ag.tenor_months).quantize(Decimal("0.01"))
    share = (monthly_interest * seller_share_rate(db)).quantize(Decimal("0.01"))
    order = db.get(Order, ag.application.order_id)
    if share > 0 and order:
        ledger.post(db, key=f"bnpl:{ag.id}:share:{inst.sequence}", kind="flex_seller_share",
                    reference=order.order_number,
                    description=f"Goods Flex seller share for {order.order_number} instalment {inst.sequence}",
                    legs=[ledger.debit(ledger.FLEX_SELLER_SHARE, share),
                          ledger.credit(ledger.seller_payable(order.seller_id), share)])
    if order:
        seller = db.get(SellerProfile, order.seller_id)
        if seller and (released_principal + share) > 0:
            notify(db, seller.user_id, "funds_released", "Goods Flex instalment received",
                   f"₦{released_principal + share:,.2f} for order {order.order_number} has been released to your wallet.",
                   link=f"/seller/orders/{order.id}")


def pay_installment(db: Session, user: User, installment_id) -> Payment:
    inst = db.query(Installment).filter_by(id=installment_id).with_for_update().one_or_none()
    if not inst:
        raise NotFound("Instalment not found")
    ag = db.get(FinancingAgreement, inst.agreement_id)
    if ag.application.user_id != user.id:
        raise NotFound("Instalment not found")
    if inst.status not in life.PAYABLE_INSTALMENT:
        raise InvalidState("This instalment is not payable")
    if ag.status not in life.PAYABLE_PLAN:
        raise InvalidState("This plan is not active")
    due = inst.amount - inst.amount_paid
    # One open payment per instalment: a second tap reuses it instead of creating a second charge.
    open_pay = db.scalars(select(Payment).where(Payment.installment_id == inst.id,
                                                Payment.purpose == PaymentPurpose.BNPL_INSTALLMENT,
                                                Payment.status == "initialized", Payment.amount == due)
                          .order_by(Payment.created_at.desc())).first()
    if open_pay:
        return open_pay
    pay = payments.create_payment(db, user=user, purpose=PaymentPurpose.BNPL_INSTALLMENT,
                                  amount=inst.amount - inst.amount_paid, installment_id=inst.id,
                                  bnpl_application_id=ag.application_id, callback_path="/flex")
    db.commit()
    return pay


@payments.on_success(PaymentPurpose.BNPL_INSTALLMENT)
def _installment_paid(db: Session, payment: Payment) -> None:
    inst = db.query(Installment).filter_by(id=payment.installment_id).with_for_update().one()
    ag = db.query(FinancingAgreement).filter_by(id=inst.agreement_id).with_for_update().one()
    due = max(inst.amount - inst.amount_paid, Decimal("0"))
    if inst.status not in life.PAYABLE_INSTALMENT or ag.status not in life.PAYABLE_PLAN:
        due = Decimal("0")  # e.g. a duplicate payment that landed after the instalment was settled
    applied = min(payment.amount, due)
    excess = payment.amount - applied
    settled = False
    if applied > 0:
        inst.amount_paid += applied
        ag.outstanding_balance = max(ag.outstanding_balance - applied, Decimal("0"))
        db.add(Repayment(installment_id=inst.id, payment_id=payment.id, amount=applied, status="success",
                         created_at=utcnow()))
        if inst.amount_paid >= inst.amount:
            life.move_instalment(inst, InstallmentStatus.PAID)
            settled = True
    if excess > 0:
        _refund_unapplied(db, payment, excess, f"Instalment {inst.sequence} was already paid")
    db.flush()
    if settled:
        _release_bnpl_instalment(db, inst, ag)
    if all(i.status in (InstallmentStatus.PAID, InstallmentStatus.CANCELLED) for i in ag.installments):
        if ag.status in life.PAYABLE_PLAN:
            life.move_plan(ag, BnplStatus.COMPLETED)
    elif ag.status == BnplStatus.DEFAULTED and not _seriously_overdue(ag):
        life.move_plan(ag, BnplStatus.ACTIVE)  # caught up: back in good standing
    if applied > 0:
        notify(db, payment.user_id, "repayment_reminder", "Repayment received",
               f"₦{applied:,.2f} received for instalment {inst.sequence}. Outstanding: ₦{ag.outstanding_balance:,.2f}.",
               link="/flex")


def _seriously_overdue(ag: FinancingAgreement) -> bool:
    cutoff = date.today() - timedelta(days=life.DEFAULT_AFTER_DAYS)
    return any(i.status == InstallmentStatus.OVERDUE and i.due_date < cutoff for i in ag.installments)


def _refund_unapplied(db: Session, payment: Payment, amount: Decimal, reason: str) -> None:
    """Money we can't apply goes straight back to the customer — never silently kept."""
    payments.refund_payment(db, payment, amount, reason)
    if payment.installment_id:
        db.add(Repayment(installment_id=payment.installment_id, payment_id=payment.id, amount=amount,
                         status="refunded", created_at=utcnow()))
    notify(db, payment.user_id, "repayment_reminder", "Payment refunded",
           f"₦{amount:,.2f} is being refunded to you: {reason}.", link="/flex")


@payments.on_failure(PaymentPurpose.BNPL_INSTALLMENT)
def _installment_failed(db: Session, payment: Payment) -> None:
    inst = db.query(Installment).filter_by(id=payment.installment_id).with_for_update().one()
    db.add(Repayment(installment_id=inst.id, payment_id=payment.id, amount=payment.amount, status="failed",
                     created_at=utcnow()))
    if inst.status == InstallmentStatus.SCHEDULED and inst.due_date < date.today():
        life.move_instalment(inst, InstallmentStatus.OVERDUE)
    notify(db, payment.user_id, "repayment_reminder", "Repayment failed",
           f"Your payment for instalment {inst.sequence} did not go through. Please try again.", link="/flex")


def _seller_share_credits(db: Session, order: Order) -> Decimal:
    """Total financing-charge share already credited to this seller for the order."""
    code = ledger.seller_payable(order.seller_id)[0]
    amount = db.scalar(
        select(func.coalesce(func.sum(LedgerEntry.amount), 0))
        .join(LedgerTransaction, LedgerTransaction.id == LedgerEntry.transaction_id)
        .join(LedgerAccount, LedgerAccount.id == LedgerEntry.account_id)
        .where(LedgerTransaction.kind == "flex_seller_share",
               LedgerTransaction.reference == order.order_number,
               LedgerAccount.code == code, LedgerEntry.direction == EntryDirection.CREDIT)
    )
    return Decimal(amount or 0)


def _recover_released_bnpl_settlement(db: Session, order: Order, reason: str) -> None:
    """If a released Flex order is refunded/cancelled, lock the seller's proceeds in the wallet.

    Open instalment holds already block the unpaid principal; this adds a recovery hold for amounts that
    have become available (down-payment share, paid instalments, credited interest share). Already
    withdrawn money makes the wallet balance negative, so future earnings are withheld first.
    """
    esc = order.escrow
    if not esc or not esc.released_at:
        return
    open_total = db.scalar(select(func.coalesce(func.sum(WalletHold.amount), 0)).where(
        WalletHold.order_id == order.id, WalletHold.released_at.is_(None))) or Decimal("0")
    target = esc.seller_amount + _seller_share_credits(db, order)
    recovery = (target - Decimal(open_total)).quantize(Decimal("0.01"))
    if recovery <= 0:
        return
    db.add(WalletHold(seller_id=order.seller_id, order_id=order.id, amount=recovery,
                      reason="bnpl_refund_recovery",
                      note=f"Goods Flex refund recovery: {reason}"[:300]))
    seller = db.get(SellerProfile, order.seller_id)
    if seller:
        notify(db, seller.user_id, "payout_hold", "Goods Flex payout recovered",
               f"₦{recovery:,.2f} from order {order.order_number} is held in your wallet after a refund/cancellation.",
               link=f"/seller/orders/{order.id}")


def cancel_financing_for_order(db: Session, order: Order, reason: str) -> None:
    a = db.scalars(select(BnplApplication).where(BnplApplication.order_id == order.id)).first()
    if not a or a.status in (BnplStatus.CANCELLED, BnplStatus.DECLINED, BnplStatus.COMPLETED):
        return
    _recover_released_bnpl_settlement(db, order, reason)
    get_financing_provider().cancel(application_ref=a.provider_application_ref, reason=reason)
    life.move_application(a, BnplStatus.CANCELLED)
    if a.agreement and a.agreement.status != BnplStatus.COMPLETED:
        life.move_agreement(a.agreement, BnplStatus.CANCELLED)
        a.agreement.outstanding_balance = Decimal("0")
        for i in a.agreement.installments:
            if i.status not in (InstallmentStatus.PAID, InstallmentStatus.CANCELLED):
                life.move_instalment(i, InstallmentStatus.CANCELLED)


def financing_summary_for_order(db: Session, order: Order, role: str) -> dict | None:
    a = db.scalars(select(BnplApplication).where(BnplApplication.order_id == order.id)).first()
    if not a:
        return None
    out = {"application_id": str(a.id), "status": a.status, "provider": a.provider,
           "credit_decision_ref": a.credit_decision_ref if role != "seller" else None}
    if role == "seller":
        out["settlement"] = "Funded and held in escrow" if order.paid_at else "Awaiting buyer down payment"
        return out
    if a.agreement:
        ag = a.agreement
        out.update(down_payment=f"{ag.down_payment:.2f}", outstanding_balance=f"{ag.outstanding_balance:.2f}")
    return out


def agreement_out(ag: FinancingAgreement) -> dict:
    a = ag.application
    return {
        "id": str(ag.id), "application_id": str(a.id), "order_id": str(a.order_id) if a.order_id else None,
        "status": ag.status, "provider_agreement_ref": ag.provider_agreement_ref,
        "purchase_amount": f"{ag.purchase_amount:.2f}", "down_payment": f"{ag.down_payment:.2f}",
        "financed_amount": f"{ag.financed_amount:.2f}", "financing_charge": f"{ag.financing_charge:.2f}",
        "total_payable": f"{ag.total_payable:.2f}", "outstanding_balance": f"{ag.outstanding_balance:.2f}",
        "tenor_months": ag.tenor_months, "accepted_at": ag.accepted_at, "terms": ag.terms_snapshot,
        "installments": [{"id": str(i.id), "sequence": i.sequence, "due_date": i.due_date, "amount": f"{i.amount:.2f}",
                          "amount_paid": f"{i.amount_paid:.2f}", "status": i.status, "paid_at": i.paid_at}
                         for i in ag.installments],
    }


def application_out(a: BnplApplication) -> dict:
    return {"id": str(a.id), "status": a.status, "order_id": str(a.order_id) if a.order_id else None,
            "product_id": str(a.product_id), "purchase_amount": f"{a.purchase_amount:.2f}",
            "tenor_months": a.tenor_months, "decline_reason": a.decline_reason, "offer_terms": a.offer_terms,
            "offer_expires_at": a.offer_expires_at, "credit_decision_ref": a.credit_decision_ref,
            "provider": a.provider, "created_at": a.created_at,
            "agreement": agreement_out(a.agreement) if a.agreement else None}


# ---------------- jobs ----------------
def mark_overdue_and_remind(db: Session) -> dict:
    """Daily job. Rows are locked and anything being paid right now is skipped (skip_locked),
    so this can never overwrite a payment that's landing at the same moment."""
    today = date.today()
    overdue = 0
    for inst in db.scalars(select(Installment).where(Installment.status == InstallmentStatus.SCHEDULED,
                                                     Installment.due_date < today)
                           .with_for_update(skip_locked=True)).all():
        life.move_instalment(inst, InstallmentStatus.OVERDUE)
        overdue += 1
        ag = db.get(FinancingAgreement, inst.agreement_id)
        notify(db, ag.application.user_id, "repayment_reminder", "Instalment overdue",
               f"Instalment {inst.sequence} of ₦{inst.amount:,.2f} was due on {inst.due_date:%d %b}. Please pay now.",
               link="/flex")
    db.flush()  # the default check below must see the instalments just marked overdue
    # 30+ days overdue → plan is in default (still counts as the customer's running plan; they can still pay).
    cutoff = today - timedelta(days=life.DEFAULT_AFTER_DAYS)
    for inst in db.scalars(select(Installment).where(Installment.status == InstallmentStatus.OVERDUE,
                                                     Installment.due_date < cutoff)).all():
        ag = db.query(FinancingAgreement).filter_by(id=inst.agreement_id).with_for_update(skip_locked=True).one_or_none()
        if ag and ag.status == BnplStatus.ACTIVE:
            life.move_plan(ag, BnplStatus.DEFAULTED)
    reminded = 0
    soon = today + timedelta(days=3)
    for inst in db.scalars(select(Installment).where(Installment.status == InstallmentStatus.SCHEDULED,
                                                     Installment.due_date <= soon,
                                                     Installment.reminder_sent_at.is_(None))
                           .with_for_update(skip_locked=True)).all():
        ag = db.get(FinancingAgreement, inst.agreement_id)
        if ag.status != BnplStatus.ACTIVE:
            continue
        inst.reminder_sent_at = utcnow()
        reminded += 1
        notify(db, ag.application.user_id, "repayment_reminder", "Upcoming Goods Flex instalment",
               f"₦{inst.amount:,.2f} is due on {inst.due_date:%d %b %Y}.", link="/flex")
    db.commit()
    return {"overdue": overdue, "reminded": reminded}


__all__ = ["Forbidden"]
