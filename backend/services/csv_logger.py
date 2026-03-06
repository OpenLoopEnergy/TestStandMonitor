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
_DEBUG_INTERVAL_SECONDS = 0.5


async def run_logger():
    """Runs forever as a FastAPI background task (lifespan)."""
    logger.info("CSV logger started — interval: %ds normal / %ds debug", _INTERVAL_SECONDS, _DEBUG_INTERVAL_SECONDS)
    while True:
        interval = _DEBUG_INTERVAL_SECONDS if data_store.debug_mode else _INTERVAL_SECONDS
        await asyncio.sleep(interval)
        try:
            await _log_tick()
        except Exception:
            logger.exception("Error in csv_logger tick")


async def _log_tick():
    snapshot = data_store.latest.copy()

    if data_store.debug_mode:
        # Debug: log whenever in Automatic mode (pb4 == 0)
        if snapshot.get("pb4", 1) != 0:
            return
    else:
        # Normal: only log when trending
        if snapshot.get("trending") != 1:
            return

    from backend.db.database import SessionLocal
    from backend.db.models import TestLog

    tp_reversed = bool(snapshot.get("tp_reved", 0) or snapshot.get("m2_tp9a_dir", 0))

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
        tp_reversed=tp_reversed,
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
