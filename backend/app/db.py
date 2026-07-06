from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.config import get_settings


def create_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(
        settings.sqlalchemy_database_url(),
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
    )


engine = create_engine()
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def check_postgres() -> bool:
    async with engine.connect() as connection:
        await connection.exec_driver_sql("SELECT 1")
    return True


async def run_schema_migrations() -> None:
    schema_path = Path(__file__).with_name("schema.sql")
    statements = [
        statement.strip()
        for statement in schema_path.read_text(encoding="utf-8").split(";")
        if statement.strip()
    ]
    async with engine.begin() as connection:
        for statement in statements:
            await connection.exec_driver_sql(statement)
