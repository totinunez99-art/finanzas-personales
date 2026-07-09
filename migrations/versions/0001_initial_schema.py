"""Esquema inicial (docs/03, ADR-008, ADR-009).

Revision ID: 0001
Revises:
Create Date: 2026-07-06
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NOW = sa.text("now()")


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("bank", sa.String(64), nullable=False),
        sa.Column("type", sa.String(16), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("last4", sa.String(4), nullable=True),
        sa.Column("opening_balance", sa.Numeric(18, 4), nullable=False),
        sa.Column("opening_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_accounts_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_accounts"),
    )
    op.create_index("ix_accounts_user_id", "accounts", ["user_id"])

    op.create_table(
        "categories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_categories_user_id_users"),
        sa.ForeignKeyConstraint(
            ["parent_id"], ["categories.id"], name="fk_categories_parent_id_categories"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_categories"),
        sa.UniqueConstraint("user_id", "parent_id", "name", name="uq_categories_user_id"),
    )
    op.create_index("ix_categories_user_id", "categories", ["user_id"])

    op.create_table(
        "import_batches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("connector", sa.String(64), nullable=False),
        sa.Column("filename", sa.String(255), nullable=True),
        sa.Column("file_sha256", sa.String(64), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("rows_read", sa.Integer(), nullable=False),
        sa.Column("rows_inserted", sa.Integer(), nullable=False),
        sa.Column("rows_duplicated", sa.Integer(), nullable=False),
        sa.Column("rows_reconciled", sa.Integer(), nullable=False),
        sa.Column("rows_failed", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_import_batches_user_id_users"),
        sa.ForeignKeyConstraint(
            ["account_id"], ["accounts.id"], name="fk_import_batches_account_id_accounts"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_import_batches"),
        sa.UniqueConstraint("account_id", "file_sha256", name="uq_import_batches_account_id"),
    )
    op.create_index("ix_import_batches_user_id", "import_batches", ["user_id"])

    op.create_table(
        "ai_calls",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column("model_version", sa.String(64), nullable=True),
        sa.Column("prompt_id", sa.String(64), nullable=False),
        sa.Column("prompt_version", sa.String(16), nullable=False),
        sa.Column("prompt_sha256", sa.String(64), nullable=False),
        sa.Column("task", sa.String(32), nullable=False),
        sa.Column("tokens_in", sa.Integer(), nullable=False),
        sa.Column("tokens_out", sa.Integer(), nullable=False),
        sa.Column("cost_estimate", sa.Numeric(10, 6), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(8), nullable=False),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("raw_response", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_ai_calls"),
    )

    op.create_table(
        "transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("posted_at", sa.Date(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("description_raw", sa.Text(), nullable=False),
        sa.Column("description_norm", sa.Text(), nullable=False),
        sa.Column("merchant", sa.String(120), nullable=True),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column("classified_by", sa.String(8), nullable=True),
        sa.Column("classification_confidence", sa.Numeric(3, 2), nullable=True),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("source", sa.String(10), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=False),
        sa.Column("dedup_hash", sa.String(64), nullable=False),
        sa.Column("intra_day_seq", sa.Integer(), nullable=False),
        sa.Column("reconciled_with_id", sa.Uuid(), nullable=True),
        sa.Column("import_batch_id", sa.Uuid(), nullable=True),
        sa.Column("installment_info", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.CheckConstraint(
            "status IN ('provisional', 'confirmed', 'reconciled', 'orphan')",
            name="ck_transactions_status_valid",
        ),
        sa.CheckConstraint(
            "source IN ('email', 'statement', 'manual')",
            name="ck_transactions_source_valid",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_transactions_user_id_users"),
        sa.ForeignKeyConstraint(
            ["account_id"], ["accounts.id"], name="fk_transactions_account_id_accounts"
        ),
        sa.ForeignKeyConstraint(
            ["category_id"], ["categories.id"], name="fk_transactions_category_id_categories"
        ),
        sa.ForeignKeyConstraint(
            ["reconciled_with_id"],
            ["transactions.id"],
            name="fk_transactions_reconciled_with_id_transactions",
        ),
        sa.ForeignKeyConstraint(
            ["import_batch_id"],
            ["import_batches.id"],
            name="fk_transactions_import_batch_id_import_batches",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_transactions"),
        sa.UniqueConstraint("account_id", "dedup_hash", name="uq_transactions_account_id"),
    )
    op.create_index("ix_transactions_user_id", "transactions", ["user_id"])
    op.create_index("ix_transactions_account_posted", "transactions", ["account_id", "posted_at"])
    op.create_index(
        "ix_transactions_description_norm_trgm",
        "transactions",
        ["description_norm"],
        postgresql_using="gin",
        postgresql_ops={"description_norm": "gin_trgm_ops"},
    )

    op.create_table(
        "classification_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("matcher_type", sa.String(24), nullable=False),
        sa.Column("pattern", sa.Text(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("origin", sa.String(12), nullable=False),
        sa.Column("hits_count", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_from_decision_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_classification_rules_user_id_users"
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name="fk_classification_rules_category_id_categories",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_classification_rules"),
    )
    op.create_index("ix_classification_rules_user_id", "classification_rules", ["user_id"])

    op.create_table(
        "classification_decisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("transaction_id", sa.Uuid(), nullable=False),
        sa.Column("decided_by", sa.String(8), nullable=False),
        sa.Column("rule_id", sa.Uuid(), nullable=True),
        sa.Column("ai_call_id", sa.Uuid(), nullable=True),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("merchant", sa.String(120), nullable=True),
        sa.Column("confidence", sa.Numeric(3, 2), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("superseded_by_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_classification_decisions_user_id_users"
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id"],
            ["transactions.id"],
            name="fk_classification_decisions_transaction_id_transactions",
        ),
        sa.ForeignKeyConstraint(
            ["rule_id"],
            ["classification_rules.id"],
            name="fk_classification_decisions_rule_id_classification_rules",
        ),
        sa.ForeignKeyConstraint(
            ["ai_call_id"], ["ai_calls.id"], name="fk_classification_decisions_ai_call_id_ai_calls"
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name="fk_classification_decisions_category_id_categories",
        ),
        sa.ForeignKeyConstraint(
            ["superseded_by_id"],
            ["classification_decisions.id"],
            # Nombre corto deliberado: el convencional supera los 63 chars de PG.
            name="fk_decisions_superseded_by_id",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_classification_decisions"),
    )
    op.create_index(
        "ix_classification_decisions_user_id", "classification_decisions", ["user_id"]
    )
    op.create_index(
        "ix_classification_decisions_transaction_id",
        "classification_decisions",
        ["transaction_id"],
    )
    op.create_index(
        "uq_decision_current_per_tx",
        "classification_decisions",
        ["transaction_id"],
        unique=True,
        postgresql_where=sa.text("is_current"),
    )

    # FK circular rules -> decisions (use_alter en el modelo).
    # Nombre corto deliberado: el convencional supera los 63 chars de PG.
    op.create_foreign_key(
        "fk_rules_created_from_decision_id",
        "classification_rules",
        "classification_decisions",
        ["created_from_decision_id"],
        ["id"],
    )

    op.create_table(
        "exchange_rates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("rate_clp", sa.Numeric(18, 4), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_exchange_rates"),
        sa.UniqueConstraint("date", "currency", name="uq_exchange_rates_date"),
    )

    op.create_table(
        "domain_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("event_type", sa.String(48), nullable=False),
        sa.Column("entity", sa.String(32), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("actor", sa.String(64), nullable=False),
        sa.Column("correlation_id", sa.String(32), nullable=True),
        sa.Column("payload", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_domain_events"),
    )
    op.create_index("ix_domain_events_entity", "domain_events", ["entity", "entity_id"])
    op.create_index("ix_domain_events_type_time", "domain_events", ["event_type", "occurred_at"])

    op.create_table(
        "job_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_name", sa.String(64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(8), nullable=False),
        sa.Column("detail", JSONB(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_job_runs"),
    )
    op.create_index("ix_job_runs_job_name", "job_runs", ["job_name"])

    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(64), nullable=False),
        sa.Column("value", JSONB(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_by", sa.String(64), nullable=False),
        sa.PrimaryKeyConstraint("key", name="pk_app_settings"),
    )

    op.create_table(
        "unparsed_emails",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("imap_uid", sa.String(32), nullable=False),
        sa.Column("message_id", sa.String(255), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("subject", sa.String(255), nullable=True),
        sa.Column("from_addr", sa.String(255), nullable=True),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_unparsed_emails_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_unparsed_emails"),
    )
    op.create_index("ix_unparsed_emails_user_id", "unparsed_emails", ["user_id"])


def downgrade() -> None:
    op.drop_table("unparsed_emails")
    op.drop_table("app_settings")
    op.drop_table("job_runs")
    op.drop_table("domain_events")
    op.drop_table("exchange_rates")
    op.drop_constraint("fk_rules_created_from_decision_id", "classification_rules")
    op.drop_table("classification_decisions")
    op.drop_table("classification_rules")
    op.drop_table("transactions")
    op.drop_table("ai_calls")
    op.drop_table("import_batches")
    op.drop_table("categories")
    op.drop_table("accounts")
    op.drop_table("users")
