"""financial integrity triggers

* ledger_entries, ledger_transactions, escrow_events, admin_audit_logs are append-only
* each ledger transaction must balance (sum debits == sum credits) at COMMIT

Revision ID: 0002_integrity
Revises: 0a43e183394b
"""

from alembic import op

revision = "0002_integrity"
down_revision = "0a43e183394b"
branch_labels = None
depends_on = None

APPEND_ONLY = ["ledger_entries", "ledger_transactions", "escrow_events", "admin_audit_logs"]


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION goodsng_forbid_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'table % is append-only', TG_TABLE_NAME USING ERRCODE = 'integrity_constraint_violation';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    for t in APPEND_ONLY:
        op.execute(
            f"CREATE TRIGGER {t}_append_only BEFORE UPDATE OR DELETE ON {t} "
            f"FOR EACH ROW EXECUTE FUNCTION goodsng_forbid_mutation();"
        )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION goodsng_check_ledger_balance() RETURNS trigger AS $$
        DECLARE
            d numeric; c numeric; n int;
        BEGIN
            SELECT coalesce(sum(amount) FILTER (WHERE direction = 'debit'), 0),
                   coalesce(sum(amount) FILTER (WHERE direction = 'credit'), 0),
                   count(*)
              INTO d, c, n
              FROM ledger_entries WHERE transaction_id = NEW.transaction_id;
            IF n < 2 OR d <> c THEN
                RAISE EXCEPTION 'ledger transaction % is unbalanced (debits %, credits %, entries %)',
                    NEW.transaction_id, d, c, n USING ERRCODE = 'integrity_constraint_violation';
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        "CREATE CONSTRAINT TRIGGER ledger_entries_balanced AFTER INSERT ON ledger_entries "
        "DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION goodsng_check_ledger_balance();"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS ledger_entries_balanced ON ledger_entries;")
    op.execute("DROP FUNCTION IF EXISTS goodsng_check_ledger_balance();")
    for t in APPEND_ONLY:
        op.execute(f"DROP TRIGGER IF EXISTS {t}_append_only ON {t};")
    op.execute("DROP FUNCTION IF EXISTS goodsng_forbid_mutation();")
