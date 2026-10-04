"""rename wui actions permissions

Revision ID: 40420e1f410a
Revises: 203a49866db9
Create Date: 2026-10-04 22:38:49.713615

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "40420e1f410a"
down_revision: str | Sequence[str] | None = "203a49866db9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Rename the permissions guarding /actions/* endpoints from the
# wui.invigilator.* prefix to wui.actions.*, so the prefix matches which
# endpoint directory (ktp_controller/wui/actions vs.
# ktp_controller/wui/invigilator) requires them. wui.invigilator.view
# keeps its name, since it guards a view, not an action.
_RENAMES = [
    ("wui.invigilator.end-exam", "wui.actions.end-exam"),
    (
        "wui.invigilator.change-student-access-code",
        "wui.actions.change-student-access-code",
    ),
    (
        "wui.invigilator.set-exam-session-permission-to-use-browsers",
        "wui.actions.set-exam-session-permission-to-use-browsers",
    ),
]

_permissions_table = sa.table(
    "permissions",
    sa.column("dbid", sa.Integer),
    sa.column("name", sa.String),
)


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    for old_name, new_name in _RENAMES:
        conn.execute(
            sa.update(_permissions_table)
            .where(_permissions_table.c.name == old_name)
            .values(name=new_name)
        )


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    for old_name, new_name in _RENAMES:
        conn.execute(
            sa.update(_permissions_table)
            .where(_permissions_table.c.name == new_name)
            .values(name=old_name)
        )
