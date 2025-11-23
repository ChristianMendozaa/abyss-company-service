# app/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from urllib.parse import urlparse
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

if not settings.database_url or settings.database_url.strip() == "":
    raise ValueError(
        "DATABASE_URL must be set in environment variables. "
        "Format: postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres"
    )

database_url = settings.database_url.strip()

# Convert a formato async psycopg
if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
elif database_url.startswith("postgresql+asyncpg://"):
    database_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
elif not database_url.startswith("postgresql+psycopg://"):
    if database_url.startswith("postgresql+"):
        pass
    else:
        raise ValueError(
            f"Invalid DATABASE_URL format. Expected postgresql:// or postgresql+psycopg://, "
            f"got: {database_url[:30]}."
        )

try:
    parsed = urlparse(database_url)
    safe_url = f"{parsed.scheme}://{parsed.username}:***@{parsed.hostname}:{parsed.port or 5432}{parsed.path}"
    logger.info(f"Connecting to database: {safe_url}")
    if not parsed.hostname:
        raise ValueError("No se pudo extraer el hostname de DATABASE_URL")
except Exception as e:
    logger.warning(f"Could not parse database URL for logging: {e}")

try:
    engine = create_async_engine(
        database_url,
        echo=False,
        future=True,
        pool_pre_ping=True,
        connect_args={
            "connect_timeout": 10,
            "options": "-c timezone=utc",
        },
    )
except Exception as e:
    logger.error(f"Error creating database engine: {e}")
    raise

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
