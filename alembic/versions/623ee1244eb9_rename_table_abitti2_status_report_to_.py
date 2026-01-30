"""Rename table abitti2_status_report to status_report

Revision ID: 623ee1244eb9
Revises: e732695e24e1
Create Date: 2026-01-30 19:58:35.878476

"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision: str = "623ee1244eb9"
down_revision: Union[str, Sequence[str], None] = "e732695e24e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    conn.execute(text("ALTER TABLE abitti2_status_report RENAME TO status_report"))
    op.create_index(
        op.f("ix_status_report_dbrow_created_at"),
        "status_report",
        ["dbrow_created_at"],
        unique=False,
    )
    op.drop_index(
        op.f("ix_abitti2_status_report_dbrow_created_at"),
        table_name="abitti2_status_report",
    )


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    conn.execute(text("ALTER TABLE status_report RENAME TO abitti2_status_report"))
    op.create_index(
        op.f("ix_abitti2_status_report_dbrow_created_at"),
        "abitti2_status_report",
        ["dbrow_created_at"],
        unique=False,
    )
    op.drop_index(op.f("ix_status_report_dbrow_created_at"), table_name="status_report")
