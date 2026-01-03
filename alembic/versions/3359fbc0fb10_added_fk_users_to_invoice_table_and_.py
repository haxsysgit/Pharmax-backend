"""Added FK users to invoice table and added audit log table

Revision ID: 3359fbc0fb10
Revises: 9ba492a1f663
Create Date: 2026-01-03 16:31:21.830820
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3359fbc0fb10"
down_revision: Union[str, Sequence[str], None] = "9ba492a1f663"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # ---- invoices table ----
    with op.batch_alter_table("invoices") as batch_op:
        batch_op.add_column(
            sa.Column("sold_by_id", sa.String(length=36), nullable=True)
        )

        batch_op.create_foreign_key(
            "fk_invoices_sold_by_id_users",
            "users",
            ["sold_by_id"],
            ["id"],
        )

        batch_op.drop_column("sold_by_name")

    # ---- stock_adjustments table ----
    with op.batch_alter_table("stock_adjustments") as batch_op:
        batch_op.create_foreign_key(
            "fk_stock_adjustments_created_by_user_id_users",
            "users",
            ["created_by_user_id"],
            ["id"],
        )


def downgrade() -> None:
    """Downgrade schema."""

    # ---- stock_adjustments table ----
    with op.batch_alter_table("stock_adjustments") as batch_op:
        batch_op.drop_constraint(
            "fk_stock_adjustments_created_by_user_id_users",
            type_="foreignkey",
        )

    # ---- invoices table ----
    with op.batch_alter_table("invoices") as batch_op:
        batch_op.add_column(
            sa.Column("sold_by_name", sa.VARCHAR(length=100), nullable=True)
        )

        batch_op.drop_constraint(
            "fk_invoices_sold_by_id_users",
            type_="foreignkey",
        )

        batch_op.drop_column("sold_by_id")
