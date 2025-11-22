# Standard library imports
import getpass
import logging
import os
import os.path
import platform
import subprocess
import typing

# Third-party imports
from pydantic import field_validator
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict  # type: ignore

# Internal imports

# Relative imports


__all__ = [
    "PuavoSettingsSource",
    "SETTINGS",
]


_LOGGER = logging.getLogger(__file__)


class PuavoSettingsSource(PydanticBaseSettingsSource):
    def get_field_value(  # pylint: disable=too-many-branches
        self, field: FieldInfo, field_name: str
    ) -> tuple[typing.Any, str, bool]:
        field_value = field.default

        if field_name in ["hostname", "domain"]:
            puavo_filepath = f"/etc/puavo/{field_name}"
            try:
                with open(puavo_filepath, "r", encoding="utf-8") as f:
                    field_value = f.read().rstrip()
            except FileNotFoundError:
                pass
            except Exception as e:  # pylint: disable=broad-exception-caught
                _LOGGER.warning("warning: failed to read %r: %s", puavo_filepath, e)

        if field_name == "id":
            puavo_filepath = "/etc/puavo/id"
            try:
                with open(puavo_filepath, "r", encoding="utf-8") as f:
                    field_value = int(f.read().rstrip())
            except FileNotFoundError:
                pass
            except Exception as e:  # pylint: disable=broad-exception-caught
                _LOGGER.warning("warning: failed to read %r: %s", puavo_filepath, e)

        if field_name == "examomatic_host":
            try:
                field_value = (
                    subprocess.check_output(["puavo-conf", "puavo.abitti.exam_server"])
                    .rstrip()
                    .decode()
                )
            except FileNotFoundError:
                pass
            except Exception as e:  # pylint: disable=broad-exception-caught
                _LOGGER.warning(
                    "warning: failed to get puavo.abitti.exam_server: %s", e
                )

        if field_name == "examomatic_username":
            try:
                with open("/etc/puavo/ldap/dn", "r", encoding="utf-8") as f:
                    field_value = f.read().rstrip()
            except FileNotFoundError:
                pass
            except Exception as e:  # pylint: disable=broad-exception-caught
                _LOGGER.warning("warning: failed to read /etc/puavo/ldap/dn: %s", e)

        if field_name == "examomatic_password_file":
            try:
                puavo_ldap_password_file = "/etc/puavo/ldap/password"
                with open(puavo_ldap_password_file, "r", encoding="utf-8") as f:
                    if len(f.read().rstrip()) == 0:
                        raise RuntimeError(
                            f"{puavo_ldap_password_file!r} contains an empty password"
                        )
                field_value = puavo_ldap_password_file
            except FileNotFoundError:
                pass
            except Exception as e:  # pylint: disable=broad-exception-caught
                _LOGGER.warning(
                    "warning: failed to read %r': %s", puavo_ldap_password_file, e
                )

        return (field_value, field_name, False)

    def __call__(self) -> dict[str, typing.Any]:
        d: dict[str, typing.Any] = {}

        for field_name, field in self.settings_cls.model_fields.items():
            field_value, _, _ = self.get_field_value(field, field_name)
            d[field_name] = field_value

        return d


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.getenv("KTP_CONTROLLER_DOTENV", ".env"),
        env_file_encoding="utf-8",
        env_prefix="KTP_CONTROLLER_",
    )

    # .invalid is reserved IANA TLD
    examomatic_host: str = "koejakaja.example.invalid"
    examomatic_username: str = getpass.getuser()
    examomatic_password_file: str = os.path.expanduser(
        "~/ktp-controller-examomatic-password.txt"
    )
    examomatic_use_tls: bool = True
    domain: str = "example.invalid"
    hostname: str = platform.node()
    id: int = 1
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    logging_level: str = "INFO"

    @field_validator("examomatic_use_tls", mode="before")
    @classmethod
    def _validate_examomatic_use_tls(cls, v) -> bool:
        if isinstance(v, str):
            if v.lower().strip() in ["yes", "y", "true", "1"]:
                return True
            if v.lower().strip() in ["no", "n", "false", "0"]:
                return False
            raise ValueError("invalid examomatic_use_tls value", v)
        return bool(v)

    @classmethod
    def settings_customise_sources(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
            PuavoSettingsSource(settings_cls),
        )


SETTINGS = Settings()
logging.getLogger().setLevel(
    logging.getLevelNamesMapping()[SETTINGS.logging_level.upper()]
)
_LOGGER.info("Using following settings: %s", SETTINGS)
