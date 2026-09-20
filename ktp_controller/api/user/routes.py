# Standard library imports
import logging

# Third-party imports
import fastapi
import sqlalchemy.orm

# Internal imports
from ktp_controller.api import models
from ktp_controller.api.database import get_db

# Relative imports
from . import schemas

_LOGGER = logging.getLogger(__name__)


__all__ = [
    "router",
]

router = fastapi.APIRouter(tags=["user"])

# Role assigned to a username the first time it successfully logs in
# and has no roles of its own yet. Keep in sync with the seed data in
# alembic/versions/bb0203ef063b_add_users_roles_and_permissions.py
# (that migration intentionally hardcodes its own copy of this name,
# as migrations must not depend on application code that can change
# later).
_DEFAULT_ROLE_NAME = "invigilator"


@router.post(
    "/get_or_create_user_permissions",
    response_model=list[str],
    summary="Get or create user and return its effective permissions",
)
async def _get_or_create_user_permissions(
    data: schemas.GetOrCreateUserPermissionsData,
    db: sqlalchemy.orm.Session = fastapi.Depends(get_db),
) -> list[str]:
    db_user = db.query(models.User).filter_by(username=data.username).one_or_none()

    if db_user is None:
        db_user = models.User(dbid=None, username=data.username, roles=[])

        db_default_role = (
            db.query(models.Role).filter_by(name=_DEFAULT_ROLE_NAME).one_or_none()
        )
        if db_default_role is not None:
            db_user.roles.append(db_default_role)
        else:
            _LOGGER.warning(
                "default role %r does not exist, new user %r gets no roles",
                _DEFAULT_ROLE_NAME,
                data.username,
            )

        db.add(db_user)
        db.commit()
        db.refresh(db_user)

    permission_names = {
        permission.name for role in db_user.roles for permission in role.permissions
    }

    return sorted(permission_names)
