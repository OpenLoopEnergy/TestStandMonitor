import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, Text, DateTime, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import types

from backend.db.database import Base


# UUID type that works for both SQLite (stores as string) and PostgreSQL
class UUIDType(types.TypeDecorator):
    impl = types.String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return str(value) if value is not None else None

    def process_result_value(self, value, dialect):
        return uuid.UUID(value) if value is not None else None


class TestLog(Base):
    """One row per 5-second logging tick while trending is active."""
    __tablename__ = "test_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    logged_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    session_id = Column(UUIDType, nullable=True)

    # Sensor values — stored raw (same units as CAN bus)
    s1 = Column(Integer)
    sp = Column(Integer)
    tp = Column(Integer)
    cycle = Column(Integer)
    cycle_timer = Column(Integer)
    lc_setpoint = Column(Integer)
    lc_regulate = Column(Integer)
    step = Column(Text)
    f1 = Column(Float)
    f2 = Column(Float)
    f3 = Column(Float)
    t1 = Column(Integer)
    t3 = Column(Integer)
    p1 = Column(Integer)
    p2 = Column(Integer)
    p3 = Column(Integer)
    p4 = Column(Integer)
    p5 = Column(Integer)


class AppSettings(Base):
    """Key-value store for user-configurable settings (program name, input factor, etc.)."""
    __tablename__ = "app_settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text)
