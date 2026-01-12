"""smoke revision

Revision ID: 1a1aaf069c14
Revises: 3359fbc0fb10
Create Date: 2026-01-08 14:12:10.756394
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "1a1aaf069c14"
down_revision: Union[str, Sequence[str], None] = "3359fbc0fb10"
branch_labels = None
depends_on = None


def upgrade():
    # 1️⃣ Backfill existing NULL values
    op.execute(
        "UPDATE invoices SET sold_by_id = 'SYSTEM' WHERE sold_by_id IS NULL"
    )

    # 2️⃣ Enforce NOT NULL
    with op.batch_alter_table("invoices") as batch_op:
        batch_op.alter_column(
            "sold_by_id",
            existing_type=sa.String(),
            nullable=False,
        )


def downgrade():
    with op.batch_alter_table("invoices") as batch_op:
        batch_op.alter_column(
            "sold_by_id",
            existing_type=sa.String(),
            nullable=True,
        )
