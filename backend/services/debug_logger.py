"""
Background task that writes a row to debug_log every 5 seconds
when the trending signal is active (trending == 1) or log_manual is enabled.

Parallel to csv_logger.py — captures all debug-screen signals including port
status, control loops, and EE configuration.
"""
import asyncio
import logging
from datetime import datetime, timezone

from backend.services import data_store

logger = logging.getLogger(__name__)

_INTERVAL_SECONDS       = 5
_DEBUG_INTERVAL_SECONDS = 0.5


async def run_debug_logger():
    """Runs forever as a FastAPI background task (lifespan)."""
    logger.info("Debug logger started — interval: %ds normal / %ds debug",
                _INTERVAL_SECONDS, _DEBUG_INTERVAL_SECONDS)
    while True:
        interval = _DEBUG_INTERVAL_SECONDS if data_store.debug_mode else _INTERVAL_SECONDS
        await asyncio.sleep(interval)
        try:
            await _debug_tick()
        except Exception:
            logger.exception("Error in debug_logger tick")


async def _debug_tick():
    snapshot = data_store.latest.copy()

    # For the debug log, log_manual overrides everything — if the user explicitly
    # enables it, capture data regardless of automatic/manual or trending state.
    # Otherwise fall back to logging only when trending is active.
    is_trending = snapshot.get("trending") == 1
    if not data_store.log_manual and not is_trending:
        return

    from backend.db.database import SessionLocal
    from backend.db.models import DebugLog

    m1 = snapshot.get("m1_ports") or {}
    m2 = snapshot.get("m2_ports") or {}
    tp_reversed = bool(snapshot.get("tp_reved", 0) or snapshot.get("m2_tp9a_dir", 0))

    row = DebugLog(
        logged_at=datetime.now(timezone.utc),
        # Core sensors
        s1=snapshot.get("s1"),             sp=snapshot.get("sp"),
        tp=snapshot.get("tp"),             cycle=snapshot.get("cycle"),
        cycle_timer=snapshot.get("cycleTimer"),
        lc_setpoint=snapshot.get("lcSetpoint"),
        lc_regulate=snapshot.get("lcRegulate"),
        step=snapshot.get("step"),
        f1=snapshot.get("f1"),             f2=snapshot.get("f2"),
        f3=snapshot.get("f3"),             t1=snapshot.get("t1"),
        t3=snapshot.get("t3"),             p1=snapshot.get("p1"),
        p2=snapshot.get("p2"),             p3=snapshot.get("p3"),
        p4=snapshot.get("p4"),             p5=snapshot.get("p5"),
        tp_reversed=tp_reversed,
        ee_dir_switch=snapshot.get("ee_dir_switch"),
        trending=snapshot.get("trending", 0),
        # Machine state
        started=snapshot.get("started"),   stopped=snapshot.get("stopped"),
        e_stopped=snapshot.get("e_stopped"),
        # M1 commands
        sol_a=snapshot.get("sol_a"),       sol_b=snapshot.get("sol_b"),
        tp9a_enable=snapshot.get("tp9a_enable"),
        tp9a_dir=snapshot.get("tp9a_dir"),
        # LC1 control loop
        lc1=snapshot.get("lc1"),
        lc1_feedback=snapshot.get("lc1_feedback"),
        lc1_enable=snapshot.get("lc1_enable"),
        lc1_state=snapshot.get("lc1_state"),
        # SP circuit
        sp_feedback=snapshot.get("sp_feedback"),
        sp_enable=snapshot.get("sp_enable"),
        sp_regulate=snapshot.get("sp_regulate"),
        sp_rev=snapshot.get("sp_rev"),
        # M2 data
        m2_pot=snapshot.get("m2_pot"),
        m2_tp9a=snapshot.get("m2_tp9a"),
        m2_tp9a_dir=snapshot.get("m2_tp9a_dir"),
        # M1 port flags (flattened from nested dict)
        m1_sp_open=m1.get("sp_open"),             m1_sp_short=m1.get("sp_short"),
        m1_sp_enable_open=m1.get("sp_enable_open"),
        m1_sp_enable_short=m1.get("sp_enable_short"),
        m1_sp_rev_open=m1.get("sp_rev_open"),     m1_sp_rev_short=m1.get("sp_rev_short"),
        m1_tp_open=m1.get("tp_open"),             m1_tp_short=m1.get("tp_short"),
        m1_tp_enable_open=m1.get("tp_enable_open"),
        m1_tp_enable_short=m1.get("tp_enable_short"),
        m1_tp_rev_open=m1.get("tp_rev_open"),     m1_tp_rev_short=m1.get("tp_rev_short"),
        m1_lc1_open=m1.get("lc1_open"),           m1_lc1_short=m1.get("lc1_short"),
        m1_lc1_pwr_open=m1.get("lc1_pwr_open"),   m1_lc1_pwr_short=m1.get("lc1_pwr_short"),
        m1_led_open=m1.get("led_open"),            m1_led_short=m1.get("led_short"),
        m1_blink=m1.get("m1_blink"),
        # M2 port flags (flattened from nested dict)
        m2_polarity_open=m2.get("polarity_open"),  m2_polarity_short=m2.get("polarity_short"),
        m2_stop_lamp_open=m2.get("stop_lamp_open"),
        m2_stop_lamp_short=m2.get("stop_lamp_short"),
        m2_sol_a_open=m2.get("sol_a_open"),        m2_sol_a_short=m2.get("sol_a_short"),
        m2_sol_b_open=m2.get("sol_b_open"),        m2_sol_b_short=m2.get("sol_b_short"),
        m2_tp9a_open=m2.get("tp9a_open"),          m2_tp9a_short=m2.get("tp9a_short"),
        m2_tp9a_fwd_open=m2.get("tp9a_fwd_open"),  m2_tp9a_fwd_short=m2.get("tp9a_fwd_short"),
        m2_tp9a_rev_open=m2.get("tp9a_rev_open"),  m2_tp9a_rev_short=m2.get("tp9a_rev_short"),
        m2_blink=m2.get("m2_blink"),               m2_supply_voltage=m2.get("supply_voltage"),
        # EE motor config
        ee_sm_rpm=snapshot.get("ee_sm_rpm"),       ee_sm_rate=snapshot.get("ee_sm_rate"),
        ee_sm_timer=snapshot.get("ee_sm_timer"),   ee_cycle_delay=snapshot.get("ee_cycle_delay"),
        # EE cycle profile
        ee_cycle_time1=snapshot.get("ee_cycle_time1"),
        ee_cycle_time2=snapshot.get("ee_cycle_time2"),
        ee_cycle_time3=snapshot.get("ee_cycle_time3"),
        ee_cycle_time4=snapshot.get("ee_cycle_time4"),
        ee_cycle_time5=snapshot.get("ee_cycle_time5"),
        ee_cycle_psi1=snapshot.get("ee_cycle_psi1"),
        ee_cycle_psi2=snapshot.get("ee_cycle_psi2"),
        ee_cycle_psi3=snapshot.get("ee_cycle_psi3"),
        ee_cycle_psi4=snapshot.get("ee_cycle_psi4"),
        ee_cycle_psi5=snapshot.get("ee_cycle_psi5"),
    )

    db = SessionLocal()
    try:
        db.add(row)
        db.commit()
        # Increment broadcast counter (no full broadcast needed — counter rides
        # along with the next Pi frame's broadcast automatically)
        data_store.latest["debug_rows_logged"] = (
            data_store.latest.get("debug_rows_logged", 0) + 1
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
