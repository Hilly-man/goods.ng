"""guarantor fingerprint

Revision ID: a7c1e9f4b2d8
Revises: e513222529d6
Create Date: 2026-11-05 18:10:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7c1e9f4b2d8"
down_revision: Union[str, Sequence[str], None] = "e513222529d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("guarantors", sa.Column("bvn_fingerprint", sa.String(length=64), nullable=True))
    op.add_column("guarantors", sa.Column("amount_guaranteed", sa.Numeric(precision=18, scale=2), nullable=True))
    op.create_index(op.f("ix_guarantors_bvn_fingerprint"), "guarantors", ["bvn_fingerprint"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_guarantors_bvn_fingerprint"), table_name="guarantors")
    op.drop_column("guarantors", "amount_guaranteed")
    op.drop_column("guarantors", "bvn_fingerprint")
