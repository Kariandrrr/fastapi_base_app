import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
from urllib.parse import quote_plus

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)

from src.core.config import settings

log = logging.getLogger(__name__)


class DBHelper:
    def __init__(
        self,
        url: str,
        echo: bool = False,
        echo_pool: bool = False,
        pool_size: int = 5,
        max_overflow: int = 10,
    ) -> None:
        self.engine: AsyncEngine = create_async_engine(
            url=url,
            echo=echo,
            echo_pool=echo_pool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,
            pool_recycle=3600,
        )

        self.session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )

    async def dispose(self) -> None:
        await self.engine.dispose()

    async def check_connection(self) -> bool:
        try:
            async with self.engine.connect() as conn:
                await conn.execute("SELECT 1")
            return True
        except Exception as e:
            log.error(f"Database connection check failed: {e}")
            return False

    @asynccontextmanager
    async def session_getter(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.session_factory() as session:
            yield session


def build_db_url(db_cfg) -> str:
    driver = getattr(db_cfg, "driver", None) or "postgresql+asyncpg"
    host = getattr(db_cfg, "host", None) or "localhost"
    port = getattr(db_cfg, "port", None)
    if port is None:
        port = 5432
    else:
        try:
            port = int(port)
        except Exception:
            raise ValueError(f"Invalid DB port: {port!r}")

    user = getattr(db_cfg, "user", None)
    password = getattr(db_cfg, "password", None)
    dbname = getattr(db_cfg, "dbname", None) or ""

    auth = ""
    if user:
        u = quote_plus(str(user))
        p = quote_plus(str(password)) if password else ""
        auth = f"{u}:{p}@" if p else f"{u}@"

    # Собираем URL
    # Если dbname пустой, оставляем без /dbname
    db_part = f"/{dbname}" if dbname else ""
    return f"{driver}://{auth}{host}:{port}{db_part}"


try:
    db_url: str = build_db_url(settings.db)
except Exception as e:
    log.error("Failed to build DB URL from settings: %s", e)
    raise

safe_url = db_url
if settings.db.password:
    safe_url = db_url.replace(str(settings.db.password), "****")
log.info("Database URL: %s", safe_url)


db_helper: DBHelper = DBHelper(
    url=db_url,
    echo=bool(settings.db.echo),
    echo_pool=bool(settings.db.echo_pool),
    pool_size=int(getattr(settings.db, "pool_size", 5) or 5),
    max_overflow=int(getattr(settings.db, "max_overflow", 10) or 10),
)


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    async with db_helper.session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with get_db_context() as session:
        yield session
