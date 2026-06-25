from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    secret_key: str
    db_password: str = "vera_secure_pass_123"
    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    upload_dir: str = "./uploads"
    max_file_size_mb: int = 100
    mathpix_app_id: str = ""
    mathpix_app_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    tesseract_cmd: str = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="VERA_",
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
