"""totp two-factor authentication

Revision ID: b2c3d4e5f6a7
Revises: a7c1e9f4b2d8
Create Date: 2026-11-05 19:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a7c1e9f4b2d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("users", sa.Column("totp_secret_enc", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("totp_enabled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("totp_recovery_hashes", postgresql.ARRAY(sa.String(length=64)),
                                     server_default=sa.text("'{}'"), nullable=False))
    op.add_column("users", sa.Column("totp_last_counter", sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "totp_last_counter")
    op.drop_column("users", "totp_recovery_hashes")
    op.drop_column("users", "totp_enabled_at")
    op.drop_column("users", "totp_secret_enc")
