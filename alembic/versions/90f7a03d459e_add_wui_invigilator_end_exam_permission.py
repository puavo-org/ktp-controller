"""add wui.invigilator.end-exam permission

Revision ID: 90f7a03d459e
Revises: bb0203ef063b
Create Date: 2026-09-25 19:12:24.398579

"""

import datetime
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "90f7a03d459e"
down_revision: str | Sequence[str] | None = "bb0203ef063b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Seed data: grant the default "invigilator" role the permission to
# end individual student exams from the WUI invigilator page.
_INVIGILATOR_ROLE_NAME = "invigilator"
_INVIGILATOR_END_EXAM_PERMISSION_NAME = "wui.invigilator.end-exam"

_permissions_table = sa.table(
    "permissions",
    sa.column("dbid", sa.Integer),
    sa.column("dbrow_created_at", sa.DateTime),
    sa.column("name", sa.String),
)
_roles_table = sa.table(
    "roles",
    sa.column("dbid", sa.Integer),
    sa.column("name", sa.String),
)
_role_permission_table = sa.table(
    "role_permission",
    sa.column("role_dbid", sa.Integer),
    sa.column("permission_dbid", sa.Integer),
)


def _select_permission_dbid(conn: sa.Connection) -> int | None:
    return conn.execute(
        sa.select(_permissions_table.c.dbid).where(
            _permissions_table.c.name == _INVIGILATOR_END_EXAM_PERMISSION_NAME
        )
    ).scalar_one_or_none()


def upgrade() -> None:
    """Upgrade schema."""
    now = datetime.datetime.utcnow()

    conn = op.get_bind()

    conn.execute(
        sa.insert(_permissions_table).values(
            dbrow_created_at=now, name=_INVIGILATOR_END_EXAM_PERMISSION_NAME
        )
    )
    permission_dbid = _select_permission_dbid(conn)

    role_dbid = conn.execute(
        sa.select(_roles_table.c.dbid).where(
            _roles_table.c.name == _INVIGILATOR_ROLE_NAME
        )
    ).scalar_one()

    conn.execute(
        sa.insert(_role_permission_table).values(
            role_dbid=role_dbid, permission_dbid=permission_dbid
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()

    permission_dbid = _select_permission_dbid(conn)
    if permission_dbid is None:
        return

    conn.execute(
        sa.delete(_role_permission_table).where(
            _role_permission_table.c.permission_dbid == permission_dbid
        )
    )
    conn.execute(
        sa.delete(_permissions_table).where(
            _permissions_table.c.dbid == permission_dbid
        )
    )
