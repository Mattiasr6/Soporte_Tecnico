from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = ""
    JWT_SECRET: str = ""
    # Comma-separated browser origins allowed by CORS. Empty (the default) adds no
    # CORS middleware at all, so deployments that do not set it are unchanged.
    CORS_ORIGINS: str = ""
    # Files of the asignacion module (shift report photos...). Empty = the
    # backend's own `data/asignacion` folder (git-ignored, mounted volume in prod).
    ASIGNACION_DATA_DIR: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @model_validator(mode="after")
    def _require_env(self):
        missing = [k for k in ("DATABASE_URL", "JWT_SECRET") if not getattr(self, k)]
        if missing:
            raise ValueError(f"Falta {', '.join(missing)}")
        return self


settings = Settings()
