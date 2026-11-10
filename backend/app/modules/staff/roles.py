"""Built-in admin roles. Seeded into `admin_roles` (is_system=True); super admins can add custom roles."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import AdminPermission as P

PERMISSION_LABELS: dict[str, tuple[str, str]] = {
    # code: (group, label)
    P.ANALYTICS_VIEW: ("Overview", "View dashboard & analytics"),
    P.USERS_MANAGE: ("Customers", "View and enable/disable customer accounts"),
    P.SELLERS_VERIFY: ("Sellers", "Verify sellers (KYC) and suspend stores"),
    P.LISTINGS_MODERATE: ("Marketplace", "Moderate listings"),
    P.CATEGORIES_MANAGE: ("Marketplace", "Manage categories"),
    P.REVIEWS_MODERATE: ("Marketplace", "Moderate reviews"),
    P.REPORTS_MANAGE: ("Marketplace", "Handle user reports"),
    P.PROMOTIONS_MANAGE: ("Marketplace", "Manage promotions"),
    P.SUBSCRIPTIONS_MANAGE: ("Marketplace", "Manage premium subscriptions & plans"),
    P.ORDERS_VIEW: ("Orders & money", "View orders"),
    P.PAYMENTS_VIEW: ("Orders & money", "View payments, escrow & ledger"),
    P.PAYOUTS_APPROVE: ("Orders & money", "Review and approve seller withdrawals"),
    P.DISPUTES_RESOLVE: ("Orders & money", "Resolve disputes"),
    P.REFUNDS_REQUEST: ("Orders & money", "Request refunds"),
    P.REFUNDS_APPROVE: ("Orders & money", "Approve refunds (second approver)"),
    P.BNPL_VIEW: ("Orders & money", "Monitor Goods Flex (BNPL)"),
    P.SETTINGS_MANAGE: ("System", "Change platform settings (fees, Flex rules)"),
    P.AUDIT_VIEW: ("System", "View audit logs"),
}

SUPER_ADMIN = "super_admin"

SYSTEM_ROLES: list[dict] = [
    {"code": SUPER_ADMIN, "name": "Super Admin",
     "description": "Full access. Creates staff accounts, assigns roles and manages roles.",
     "permissions": [p.value for p in P]},
    {"code": "operations_manager", "name": "Operations Manager",
     "description": "Runs day-to-day order operations: orders, payments, disputes and refund requests.",
     "permissions": [P.ANALYTICS_VIEW, P.ORDERS_VIEW, P.PAYMENTS_VIEW, P.DISPUTES_RESOLVE, P.REFUNDS_REQUEST, P.BNPL_VIEW]},
    {"code": "finance", "name": "Finance",
     "description": "Payments, escrow & ledger, refund approval and Goods Flex monitoring.",
     "permissions": [P.ANALYTICS_VIEW, P.ORDERS_VIEW, P.PAYMENTS_VIEW, P.PAYOUTS_APPROVE, P.REFUNDS_APPROVE,
                     P.BNPL_VIEW, P.AUDIT_VIEW]},
    {"code": "customer_support", "name": "Customer Support",
     "description": "Helps customers: accounts, orders, disputes and reports.",
     "permissions": [P.USERS_MANAGE, P.ORDERS_VIEW, P.DISPUTES_RESOLVE, P.REFUNDS_REQUEST, P.REPORTS_MANAGE]},
    {"code": "trust_safety", "name": "Trust & Safety",
     "description": "Keeps the marketplace safe: listings, reviews, reports and seller checks.",
     "permissions": [P.LISTINGS_MODERATE, P.REVIEWS_MODERATE, P.REPORTS_MANAGE, P.SELLERS_VERIFY, P.USERS_MANAGE]},
    {"code": "kyc_officer", "name": "KYC Officer",
     "description": "Reviews seller identity and business verification documents.",
     "permissions": [P.SELLERS_VERIFY]},
    {"code": "marketing", "name": "Marketing",
     "description": "Categories, promotions, premium plans and analytics.",
     "permissions": [P.ANALYTICS_VIEW, P.CATEGORIES_MANAGE, P.PROMOTIONS_MANAGE, P.SUBSCRIPTIONS_MANAGE]},
    {"code": "auditor", "name": "Auditor",
     "description": "Read-only oversight of orders, payments, analytics and the audit log.",
     "permissions": [P.ANALYTICS_VIEW, P.ORDERS_VIEW, P.PAYMENTS_VIEW, P.BNPL_VIEW, P.AUDIT_VIEW]},
]


def ensure_system_roles(db: Session) -> None:
    """Idempotently create/refresh the built-in roles (their permissions are defined in code)."""
    from app.models import AdminRole

    existing = {r.code: r for r in db.scalars(select(AdminRole))}
    for i, spec in enumerate(SYSTEM_ROLES):
        perms = sorted(str(getattr(p, "value", p)) for p in spec["permissions"])
        r = existing.get(spec["code"])
        if not r:
            db.add(AdminRole(code=spec["code"], name=spec["name"], description=spec["description"],
                             permissions=perms, is_system=True, sort_order=i))
        else:
            r.name, r.description, r.permissions, r.is_system, r.sort_order = spec["name"], spec["description"], perms, True, i
    db.flush()
