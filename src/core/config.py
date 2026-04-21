import logging
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, computed_field, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

LOG_DEFAULT_FORMAT = (
    "[%(asctime)s.%(msecs)03d] %(module)10s:%(lineno)-3d %(levelname)-7s - %(message)s"
)

WORKER_LOG_DEFAULT_FORMAT = "[%(asctime)s.%(msecs)03d][%(processName)s] %(module)16s:%(lineno)-3d %(levelname)-7s - %(message)s"


class RunConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000


class GunicornConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    timeout: int = 900


class LoggingConfig(BaseModel):
    log_level: Literal[
        "debug",
        "info",
        "warning",
        "error",
        "critical",
    ] = "info"
    log_format: str = LOG_DEFAULT_FORMAT
    date_format: str = "%Y-%m-%d %H:%M:%S"

    @property
    def log_level_value(self) -> int:
        return logging.getLevelNamesMapping()[self.log_level.upper()]


class ApiPrefix(BaseModel):
    prefix: str = "/api"


class DatabaseConfig(BaseModel):
    driver: str = "postgresql+asyncpg"
    echo: bool = True
    echo_pool: bool = False
    pool_size: int = 20
    max_overflow: int = 10

    user: str | None = None
    password: str | None = Field(None, repr=False)
    host: str | None = None
    port: int | None = None
    dbname: str | None = None

    naming_convention: dict[str, str] = {
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_N_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }

    @computed_field
    @property
    def url(self) -> str:
        return f"{self.driver}://{self.user}:{self.password}@{self.host}:{self.port}/{self.dbname}"


BASE_DIR = Path(__file__).parent.parent


class CookieSettings(BaseModel):
    name_access: str = "access_token"
    name_refresh: str = "refresh_token"

    secure: bool = True
    http_only: bool = True
    same_site: Literal["lax", "strict", "none"] = "lax"
    domain: str | None = None
    path: str = "/"

    max_age_access: int = 15 * 60  # 15 minutes
    max_age_refresh: int = 14 * 24 * 3600  # 14 days


class AuthJWT(BaseModel):
    private_key_path: Path = BASE_DIR.parent / "certs" / "jwt-private.pem"
    public_key_path: Path = BASE_DIR.parent / "certs" / "jwt-public.pem"
    algorithm: str = "RS256"
    access_token_expire_minutes: int = 15
    cookie: CookieSettings = CookieSettings()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env.template", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        env_nested_delimiter="__",
        env_prefix="APP_CONFIG__",
    )
    run: RunConfig = RunConfig()
    gunicorn: GunicornConfig = GunicornConfig()
    logging: LoggingConfig = LoggingConfig()
    api: ApiPrefix = ApiPrefix()
    db: DatabaseConfig = DatabaseConfig()
    auth_jwt: AuthJWT = AuthJWT()


settings = Settings()
