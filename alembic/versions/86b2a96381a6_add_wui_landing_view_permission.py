"""add wui.landing.view permission

Revision ID: 86b2a96381a6
Revises: ee4033606b43
Create Date: 2026-10-22 22:41:49.165190

"""

import datetime
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "86b2a96381a6"
down_revision: str | Sequence[str] | None = "ee4033606b43"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Seed data: grant every existing role permission to view the WUI
# landing page ("/"). Unlike other wui.* permission migrations, this
# one is not scoped to a single hardcoded role: the landing page is
# meant to be reachable by any role, present or future, so it grants
# the permission to whatever roles already exist at migration time.
_LANDING_VIEW_PERMISSION_NAME = "wui.landing.view"

_permissions_table = sa.table(
    "permissions",
    sa.column("dbid", sa.Integer),
    sa.column("dbrow_created_at", sa.DateTime),
    sa.column("name", sa.String),
)
_roles_table = sa.table(
    "roles",
    sa.column("dbid", sa.Integer),
)
_role_permission_table = sa.table(
    "role_permission",
    sa.column("role_dbid", sa.Integer),
    sa.column("permission_dbid", sa.Integer),
)


def _select_permission_dbid(conn: sa.Connection) -> int | None:
    return conn.execute(
        sa.select(_permissions_table.c.dbid).where(
            _permissions_table.c.name == _LANDING_VIEW_PERMISSION_NAME
        )
    ).scalar_one_or_none()


def upgrade() -> None:
    """Upgrade schema."""
    now = datetime.datetime.utcnow()

    conn = op.get_bind()

    conn.execute(
        sa.insert(_permissions_table).values(
            dbrow_created_at=now, name=_LANDING_VIEW_PERMISSION_NAME
        )
    )
    permission_dbid = _select_permission_dbid(conn)

    role_dbids = conn.execute(sa.select(_roles_table.c.dbid)).scalars().all()

    if role_dbids:
        conn.execute(
            sa.insert(_role_permission_table),
            [
                {"role_dbid": role_dbid, "permission_dbid": permission_dbid}
                for role_dbid in role_dbids
            ],
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
