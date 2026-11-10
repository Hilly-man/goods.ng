"""site visits for live traffic stats

Revision ID: a1b2c3d4e5f6
Revises: 7c8d9e0f1a2b
Create Date: 2026-11-10 16:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'a1b2c3d4e5f6'
down_revision: str | Sequence[str] | None = '7c8d9e0f1a2b'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'site_visits',
        sa.Column('visitor_id', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('path', sa.String(length=300), nullable=False),
        sa.Column('referrer', sa.String(length=300), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_site_visits_user_id_users'),
                                ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_site_visits')),
    )
    op.create_index(op.f('ix_site_visits_visitor_id'), 'site_visits', ['visitor_id'])
    op.create_index(op.f('ix_site_visits_user_id'), 'site_visits', ['user_id'])
    op.create_index('ix_site_visits_visitor_created', 'site_visits', ['visitor_id', 'created_at'])
    op.create_index('ix_site_visits_created', 'site_visits', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_site_visits_created', table_name='site_visits')
    op.drop_index('ix_site_visits_visitor_created', table_name='site_visits')
    op.drop_index(op.f('ix_site_visits_user_id'), table_name='site_visits')
    op.drop_index(op.f('ix_site_visits_visitor_id'), table_name='site_visits')
    op.drop_table('site_visits')
