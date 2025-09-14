from pydantic_settings import BaseSettings, SettingsConfigDict  # type: ignore


class Settings(BaseSettings):
    examomatic_host: str
    examomatic_username: str
    examomatic_password_file: str
    domain: str
    hostname: str
    id: str

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_prefix="KTP_CONTROLLER_"
    )


SETTINGS = Settings()
