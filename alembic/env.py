import os
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv  # Нужно установить: pip install python-dotenv
from sqlalchemy import engine_from_config
from sqlalchemy import pool

# 1. Сначала загружаем переменные из .env
load_dotenv()

# 2. Импортируем твои модели
# Важно: убедись, что все модели (User, FamilyGroup и т.д.)
# импортированы внутри src.core.models.base или в src.core.models/__init__.py
from src.core.models.base import Base

config = context.config

# 3. ПЕРЕХВАТЫВАЕМ URL из системы/файла .env
db_url = os.getenv("DATABASE_URL")
if db_url:
    # Принудительно вставляем URL в конфигурацию Alembic
    config.set_main_option("sqlalchemy.url", db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Указываем метаданные для autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Здесь engine_from_config теперь возьмет URL, который мы подставили выше
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
