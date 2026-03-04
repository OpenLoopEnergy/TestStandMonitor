"""
Background task that writes a row to test_log every 5 seconds
when the trending signal is active (trending == 1).

Replaces the databaseManipulation.log_data_to_csv() thread loop.
"""
import asyncio
import logging
from datetime import datetime, timezone

from backend.services import data_store

logger = logging.getLogger(__name__)

_INTERVAL_SECONDS = 5


async def run_logger():
    """Runs forever as a FastAPI background task (lifespan)."""
    logger.info("CSV logger started — interval: %ds", _INTERVAL_SECONDS)
    while True:
        await asyncio.sleep(_INTERVAL_SECONDS)
        try:
            await _log_tick()
        except Exception:
            logger.exception("Error in csv_logger tick")


async def _log_tick():
    snapshot = data_store.latest.copy()

    if snapshot.get("trending") != 1:
        return  # Not in a trending/logging state

    from backend.db.database import SessionLocal
    from backend.db.models import TestLog

    row = TestLog(
        logged_at=datetime.now(timezone.utc),
        s1=snapshot.get("s1"),
        sp=snapshot.get("sp"),
        tp=snapshot.get("tp"),
        cycle=snapshot.get("cycle"),
        cycle_timer=snapshot.get("cycleTimer"),
        lc_setpoint=snapshot.get("lcSetpoint"),
        lc_regulate=snapshot.get("lcRegulate"),
        step=snapshot.get("step"),
        f1=snapshot.get("f1"),
        f2=snapshot.get("f2"),
        f3=snapshot.get("f3"),
        t1=snapshot.get("t1"),
        t3=snapshot.get("t3"),
        p1=snapshot.get("p1"),
        p2=snapshot.get("p2"),
        p3=snapshot.get("p3"),
        p4=snapshot.get("p4"),
        p5=snapshot.get("p5"),
    )

    db = SessionLocal()
    try:
        db.add(row)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
