"""
Simulation mode — generates realistic CAN-derived data matching actual test stand output.

Real data observed from log files:
  S1: ~1200 RPM (±50)        SP: 1200 RPM
  TP: cycles 0→1000→0        F1 raw: ~5700 at full TP, ~20 at idle
  F2 raw: ~1000               F3 raw: ~20715 when active, ~182 idle
  T1 raw: ~1408 (140.8°F)    T3 raw: ~756 (75.6°F)
  P1: 439-2211 PSI            P2: ~290 PSI
  P3: ~490 PSI                P4: 0   P5: ~450-1000 PSI
  LCSetpoint: 1000/2000/etc   CycleTimer: counts down from ~5800

Used when MOCK_MODE=true so the full stack can be developed and tested
without a physical Raspberry Pi connected.
"""
import asyncio
import csv
import logging
import os
import random

logger = logging.getLogger(__name__)

SIM_CSV = os.getenv("SIM_CSV", os.path.join(os.path.dirname(__file__), "..", "log_data.csv"))
SIM_INTERVAL = float(os.getenv("SIM_INTERVAL", "0.5"))

# Realistic bubble/step states for a normal test cycle
_STATES = [
    (101, "B1: Wait for Start"),
    (130, "B30: Tp Ramp Up"),
    (157, "B57: TP Ramp Up"),
    (159, "B59: Delay"),
    (156, "B56: Check If In Test"),
    (152, "B52: TP Ramp Down"),
    (160, "B60: Tp Ramp Down"),
]


def _load_csv_rows():
    """Try to load real CSV rows; returns None if unavailable."""
    if not os.path.isfile(SIM_CSV):
        logger.warning("SIM_CSV not found at %s — using synthetic data", SIM_CSV)
        return None

    rows = []
    skip_keywords = ["Program Name", "Description", "Employee ID", "Comp Set",
                     "Input Factor", "Serial Number", "Customer ID"]
    try:
        with open(SIM_CSV, newline="", encoding="utf-8") as f:
            lines = [l for l in f if not any(kw in l for kw in skip_keywords)]
        reader = csv.DictReader(iter(lines))
        for row in reader:
            if row.get("S1"):
                rows.append(row)
    except Exception as e:
        logger.warning("Error reading sim CSV: %s", e)
        return None

    return rows if rows else None


def _row_to_frame(row: dict) -> dict:
    """
    Convert a log_data.csv row into a live data frame.
    log_data.csv stores RAW CAN values (F1 is raw centi-units, not scaled).
    """
    def _int(key, default=0):
        try:
            return int(float(row.get(key) or default))
        except (ValueError, TypeError):
            return default

    s1 = _int("S1")
    return {
        "s1":        s1,
        "sp":        _int("SP"),
        "tp":        _int("TP"),
        "cycle":     _int("Cycle"),
        "cycleTimer":_int("Cycle Timer"),
        "lcSetpoint":_int("LCSetpoint"),
        "lcRegulate":_int("LC Regulate"),
        "step":      row.get("Step", "Unknown"),
        "trending":  1 if s1 > 900 else 0,
        "f1":        _int("F1"),    # raw centi-units in log_data.csv
        "f2":        _int("F2"),    # raw
        "f3":        _int("F3"),    # raw
        "t1":        _int("T1"),    # raw (÷10 = °F)
        "t3":        _int("T3"),    # raw (÷10 = °F)
        "p1":        _int("P1"),
        "p2":        _int("P2"),
        "p3":        _int("P3"),
        "p4":        _int("P4"),
        "p5":        _int("P5"),
        "delay":     0,
        "pi_connected": True,
    }


def _synthetic_frame(tick: int) -> dict:
    """
    Generate a synthetic frame that closely mimics real test stand data.
    Cycles through a realistic test sequence over ~120 ticks (~60 seconds).
    """
    CYCLE_LEN = 120
    pos = tick % CYCLE_LEN
    cycle_num = tick // CYCLE_LEN + 1

    # TP ramp: 0→1000 over first 20 ticks, hold 60, ramp down 20, hold 20
    if pos < 20:
        tp = int(pos * 50)
        state_idx = 1  # Ramp Up
    elif pos < 80:
        tp = 1000 + random.randint(-5, 5)
        state_idx = 4  # Check If In Test
    elif pos < 100:
        tp = int((100 - pos) * 50)
        state_idx = 5  # TP Ramp Down
    else:
        tp = 0
        state_idx = 0  # Wait for Start

    tp = max(0, min(1023, tp))
    at_full_speed = tp >= 950

    s1 = 1200 + random.randint(-40, 40)
    lc_set = cycle_num * 1000

    # F1: ~5700 raw at full TP (→57 GPM), ~20 raw at idle
    f1 = random.randint(5500, 5900) if at_full_speed else random.randint(15, 25)
    f2 = random.randint(960, 1040)       # raw ~1000
    f3 = 20715 if at_full_speed else 182

    t1 = 1408 + random.randint(-8, 8)   # ~140.8°F
    t3 = 756 + random.randint(-6, 6)    # ~75.6°F

    p1 = (lc_set + random.randint(-50, 100)) if at_full_speed else random.randint(430, 460)
    p2 = random.randint(285, 295)
    p3 = random.randint(470, 510)
    p4 = 0
    p5 = random.randint(600, 1050) if at_full_speed else random.randint(440, 480)

    hold_pos = pos - 20
    cycle_timer = max(0, 5800 - hold_pos * 97) if at_full_speed else 0

    _, step_str = _STATES[state_idx]

    return {
        "s1": s1, "sp": 1200, "tp": tp,
        "cycle": cycle_num, "cycleTimer": cycle_timer,
        "lcSetpoint": lc_set, "lcRegulate": 1 if at_full_speed else 0,
        "step": step_str,
        "trending": 1 if at_full_speed else 0,
        "f1": f1, "f2": f2, "f3": f3,
        "t1": t1, "t3": t3,
        "p1": p1, "p2": p2, "p3": p3, "p4": p4, "p5": p5,
        "delay": 0, "pi_connected": True,
    }


async def run_sim():
    """Asyncio task — pushes simulated frames into data_store indefinitely."""
    from backend.services import data_store

    rows = _load_csv_rows()
    source = "CSV replay" if rows else "synthetic data"
    logger.info("Sim mode active — source: %s", source)

    tick = 0
    while True:
        frame = _row_to_frame(rows[tick % len(rows)]) if rows else _synthetic_frame(tick)
        await data_store.update(frame)
        tick += 1
        await asyncio.sleep(SIM_INTERVAL)
