# Third-party imports
import pydantic

# Internal imports
import ktp_controller.pydantic

# Relative imports


__all__ = [
    # Types:
    "GetOrCreateUserPermissionsData",
]


# Types:


class GetOrCreateUserPermissionsData(ktp_controller.pydantic.BaseModel):
    username: pydantic.StrictStr
