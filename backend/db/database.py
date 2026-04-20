import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dev.db")

# SQLite needs check_same_thread=False; PostgreSQL doesn't need it
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


_DEFAULT_SETTINGS = {
    "programName":    "",
    "description":    "",
    "compSet":        "0",
    "inputFactor":    "11",
    "inputFactorType":"cu/in",
    "serialNumber":   "0",
    "employeeId":     "0",
    "customerId":     "0",
}


def init_db():
    from backend.db import models  # noqa: F401 — ensure models are registered
    from backend.db.models import AppSettings
    Base.metadata.create_all(bind=engine)

    # Add new nullable columns to existing tables without dropping data
    with engine.connect() as conn:
        for col_def in ("ALTER TABLE test_log ADD COLUMN trending INTEGER",):
            try:
                conn.execute(__import__("sqlalchemy").text(col_def))
                conn.commit()
            except Exception:
                pass  # Column already exists — safe to ignore

    # Seed defaults only for keys that don't already exist
    db = SessionLocal()
    try:
        for key, value in _DEFAULT_SETTINGS.items():
            if not db.query(AppSettings).filter(AppSettings.key == key).first():
                db.add(AppSettings(key=key, value=value))
        db.commit()
    finally:
        db.close()
