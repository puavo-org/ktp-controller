from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    exam_o_matic_host: str
    exam_o_matic_username: str
    exam_o_matic_password_file: str
    domain: str
    hostname: str
    id: str

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_prefix="KTP_CONTROLLER_"
    )


SETTINGS = Settings()
