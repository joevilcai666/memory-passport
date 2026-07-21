"""Persist export download token plaintext on export_jobs.

The status endpoint needs the plaintext token to build the ``download_url``
(the SHA-256 hash stored since 0007 is unrecoverable). Previously the plaintext
lived only in an in-process Python dict, which silently broke under multiple
uvicorn workers or a restart. This column is the durable replacement.

One-shot: the application clears it on successful download and on job failure.

Revision ID: 0008_export_token_plaintext
Revises: 0007_exports_user_deletion
Create Date: 2026-07-21 00:00:07
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008_export_token_plaintext"
down_revision: str | None = "0007_exports_user_deletion"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "export_jobs",
        sa.Column("download_token", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("export_jobs", "download_token")
