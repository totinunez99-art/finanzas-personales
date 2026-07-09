"""Tabla unrecognized_files para el Import Wizard (docs/14).

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-06
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NOW = sa.text("now()")


def upgrade() -> None:
    op.create_table(
        "unrecognized_files",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("file_sha256", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("extension", sa.String(16), nullable=False),
        sa.Column("header_preview", sa.String(500), nullable=True),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_unrecognized_files_user_id_users"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_unrecognized_files"),
        sa.UniqueConstraint("file_sha256", name="uq_unrecognized_files_file_sha256"),
    )
    op.create_index("ix_unrecognized_files_user_id", "unrecognized_files", ["user_id"])


def downgrade() -> None:
    op.drop_table("unrecognized_files")
