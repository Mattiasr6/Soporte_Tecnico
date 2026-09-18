from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = ""
    JWT_SECRET: str = ""

    @model_validator(mode="after")
    def _require_env(self):
        missing = [k for k in ("DATABASE_URL", "JWT_SECRET") if not getattr(self, k)]
        if missing:
            raise ValueError(f"Falta {', '.join(missing)}")
        return self


settings = Settings()
