from pydantic import field_validator
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/gerencia_costos"
    DATABASE_URL_TEST: str = "postgresql://postgres:postgres@localhost:5432/gerencia_costos_test"
    # Solo para migraciones puntuales contra produccion (alembic). Vacia por defecto.
    DATABASE_URL_PROD: str = ""
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    @field_validator("DATABASE_URL", "DATABASE_URL_TEST", "DATABASE_URL_PROD", mode="before")
    @classmethod
    def _normalizar_esquema(cls, v: str) -> str:
        # Prisma y Heroku entregan postgres://; SQLAlchemy 2 solo acepta postgresql://
        if isinstance(v, str) and v.startswith("postgres://"):
            return "postgresql://" + v[len("postgres://"):]
        return v

    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
