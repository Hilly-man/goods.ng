"""Create the first super admin (bootstrap) — run once per environment from a trusted shell:

    python -m app.create_super_admin --email ceo@goods.ng --name "Ada Founder"

Prints a one-time invitation link (valid 72h) for setting the password; the password itself is never
typed into a terminal or stored in shell history. Refuses if an active super admin already exists, unless
--force is given (e.g. to recover after losing access).
"""

import argparse
import sys

from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.security import hash_password, new_opaque_token
from app.models import AdminRole, Profile, User
from app.models.enums import AccountType, UserRole
from app.modules.staff.roles import SUPER_ADMIN, ensure_system_roles
from app.modules.staff.router import _send_invite


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--email", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--force", action="store_true", help="allow even if an active super admin exists")
    a = ap.parse_args()
    email = a.email.strip().lower()
    with SessionLocal() as db:
        ensure_system_roles(db)
        existing = db.scalars(select(User).where(User.account_type == AccountType.STAFF, User.role == UserRole.SUPER_ADMIN,
                                                 User.is_active.is_(True), User.deleted_at.is_(None))).first()
        if existing and not a.force:
            print(f"An active super admin already exists ({existing.email}). Use the admin console to invite staff, "
                  "or pass --force to create another.", file=sys.stderr)
            return 1
        if db.scalars(select(User).where(User.email == email)).first():
            print("That email already has an account. Use a separate work email for staff.", file=sys.stderr)
            return 1
        role = db.scalars(select(AdminRole).where(AdminRole.code == SUPER_ADMIN)).one()
        u = User(email=email, full_name=a.name, account_type=AccountType.STAFF, role=UserRole.SUPER_ADMIN,
                 admin_role_id=role.id, admin_permissions=[], password_hash=hash_password(new_opaque_token()))
        u.profile = Profile()
        db.add(u)
        db.flush()
        link = _send_invite(db, u, u)
        db.commit()
    print(f"Super admin created for {email}.\nOpen this link to set the password (valid 72 hours):\n{link}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
