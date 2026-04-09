# Standard library imports
import os
import os.path
import platform
import subprocess
import typing

# Third-party imports
from pydantic import field_validator, PositiveInt, StrictBool
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)  # type: ignore

# Internal imports

# Do NOT import ktp_controller. This module is imported by
# ktp_controller, no thanks for cyclic dependencies.

__all__ = [
    "Settings",
]


class _PuavoSettingsSource(PydanticBaseSettingsSource):
    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> tuple[typing.Any, str, bool]:
        field_value = field.default

        if not os.path.exists("/etc/puavo"):
            return (field_value, field_name, False)

        if field_name in ["hostname", "domain"]:
            puavo_filepath = f"/etc/puavo/{field_name}"
            with open(puavo_filepath, "r", encoding="utf-8") as f:
                field_value = f.read().rstrip()

        elif field_name == "id":
            puavo_filepath = "/etc/puavo/id"
            with open(puavo_filepath, "r", encoding="utf-8") as f:
                field_value = int(f.read().rstrip())

        elif field_name == "examomatic_host":
            field_value = (
                subprocess.check_output(["puavo-conf", "puavo.abitti.exam_server"])
                .rstrip()
                .decode()
            )

        elif field_name == "examomatic_username":
            with open("/etc/puavo/ldap/dn", "r", encoding="utf-8") as f:
                field_value = f.read().rstrip()

        elif field_name == "examomatic_password_file":
            field_value = "/etc/puavo/ldap/password"

        return (field_value, field_name, False)

    def __call__(self) -> dict[str, typing.Any]:
        d: dict[str, typing.Any] = {}

        for field_name, field in self.settings_cls.model_fields.items():
            field_value, _, _ = self.get_field_value(field, field_name)
            d[field_name] = field_value

        return d


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.getenv("KTP_CONTROLLER_DOTENV", "ktp_controller.env"),
        env_file_encoding="utf-8",
        env_prefix="KTP_CONTROLLER_",
    )

    examomatic_host: str
    examomatic_username: str
    examomatic_password_file: str
    examomatic_use_tls: StrictBool = True
    examomatic_ping_interval_sec: PositiveInt = 30
    answer_transfer_interval_sec: PositiveInt = 300
    refresh_exams_interval_sec: PositiveInt = 180
    domain: str
    hostname: str = platform.node()
    id: PositiveInt
    api_host: str = "127.0.0.1"
    api_port: PositiveInt = 8000
    logging_level: str = "INFO"
    db_path: str = "ktp_controller.sqlite"
    abitti2_allow_students_to_use_browsers: StrictBool = False
    abitti2_change_student_access_code_automatically: StrictBool = True

    @field_validator("examomatic_use_tls", mode="before")
    @classmethod
    def _validate_examomatic_use_tls(cls, v) -> typing.Any:
        if isinstance(v, str):
            if v.lower().strip() in ["yes", "y", "true", "1"]:
                return True
            if v.lower().strip() in ["no", "n", "false", "0"]:
                return False
            raise ValueError("invalid examomatic_use_tls value", v)
        return v

    @field_validator("abitti2_allow_students_to_use_browsers", mode="before")
    @classmethod
    def _validate_abitti2_allow_students_to_use_browsers(cls, v) -> typing.Any:
        if isinstance(v, str):
            if v.lower().strip() in ["yes", "y", "true", "1"]:
                return True
            if v.lower().strip() in ["no", "n", "false", "0"]:
                return False
            raise ValueError("invalid abitti2_allow_students_to_use_browsers value", v)
        return v

    @field_validator("abitti2_change_student_access_code_automatically", mode="before")
    @classmethod
    def _validate_abitti2_change_student_access_code_automatically(
        cls, v
    ) -> typing.Any:
        if isinstance(v, str):
            if v.lower().strip() in ["yes", "y", "true", "1"]:
                return True
            if v.lower().strip() in ["no", "n", "false", "0"]:
                return False
            raise ValueError(
                "invalid abitti2_change_student_access_code_automatically value", v
            )
        return v

    @classmethod
    def settings_customise_sources(
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
            _PuavoSettingsSource(settings_cls),
        )
