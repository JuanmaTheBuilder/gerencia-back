from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:Balto2018@localhost:5432/gerencia_costos"
    DATABASE_URL_TEST: str = "postgresql://postgres:Balto2018@localhost:5432/gerencia_costos_test"
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
