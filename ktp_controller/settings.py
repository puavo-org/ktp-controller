from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    exam_o_matic_host: str

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_prefix="KTP_CONTROLLER_"
    )


SETTINGS = Settings()
