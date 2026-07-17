"""Base de conocimiento de comercios + procedencia en transactions (Sprint 3 B2, docs/21).

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NOW = sa.text("now()")


def upgrade() -> None:
    op.create_table(
        "merchant_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("matcher_type", sa.String(24), nullable=False),
        sa.Column("pattern", sa.Text(), nullable=False),
        sa.Column("merchant", sa.String(120), nullable=False),
        sa.Column("origin", sa.String(12), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("hits_count", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_merchant_rules_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_merchant_rules"),
    )
    op.create_index("ix_merchant_rules_user_id", "merchant_rules", ["user_id"])

    op.add_column("transactions", sa.Column("merchant_source", sa.String(12), nullable=True))
    op.add_column("transactions", sa.Column("merchant_confidence", sa.Numeric(3, 2), nullable=True))
    op.add_column("transactions", sa.Column("merchant_rule_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_transactions_merchant_rule_id_merchant_rules",
        "transactions",
        "merchant_rules",
        ["merchant_rule_id"],
        ["id"],
    )
    # Backfill: los merchant existentes provienen de hints del parser Edwards.
    op.execute(
        "UPDATE transactions SET merchant_source = 'hint', merchant_confidence = 0.90 "
        "WHERE merchant IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_constraint("fk_transactions_merchant_rule_id_merchant_rules", "transactions")
    op.drop_column("transactions", "merchant_rule_id")
    op.drop_column("transactions", "merchant_confidence")
    op.drop_column("transactions", "merchant_source")
    op.drop_table("merchant_rules")
