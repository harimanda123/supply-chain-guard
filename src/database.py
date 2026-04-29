from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy import create_engine
from src.config import get_settings

settings = get_settings()


# ── Base class all models inherit from ────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── Engine ────────────────────────────────────────────────────────────────────
engine = create_async_engine(
    settings.database_url,
    echo=settings.app_env == "development",  # logs SQL in dev only
    connect_args={"check_same_thread": False},  # required for SQLite
)

# ── Session factory ───────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Dependency — used in FastAPI routes ───────────────────────────────────────
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Sync engine — used only by LangChain tool functions running in threads ────
_sync_url = settings.database_url.replace("+aiosqlite", "")
sync_engine = create_engine(
    _sync_url,
    connect_args={"check_same_thread": False},
)
SyncSessionLocal = __import__("sqlalchemy.orm", fromlist=["sessionmaker"]).sessionmaker(
    bind=sync_engine,
    class_=Session,
    expire_on_commit=False,
)


def get_sync_db() -> Session:
    """Return a new sync session. Caller is responsible for closing."""
    return SyncSessionLocal()


# ── Create all tables ─────────────────────────────────────────────────────────
async def init_db() -> None:
    from src.models import (  # noqa: F401 — imports trigger table registration
        disruption_event,
        shipment_status,
        inventory_position,
        production_schedule,
        financial_rule,
        carrier,
        compliance_registry,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database initialised")