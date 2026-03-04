import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import TestLog, AppSettings
from backend.services import data_store

router = APIRouter()
logger = logging.getLogger(__name__)

# Maps signal name → (column attribute on TestLog, display unit)
SIGNAL_COLUMN_MAP: dict[str, str] = {
    "S1": "s1", "SP": "sp", "TP": "tp",
    "F1": "f1", "F2": "f2", "F3": "f3",
    "T1": "t1", "T3": "t3",
    "P1": "p1", "P2": "p2", "P3": "p3", "P4": "p4", "P5": "p5",
}


def _get_input_factor(db: Session) -> float:
    row = db.query(AppSettings).filter(AppSettings.key == "inputFactor").first()
    try:
        return float(row.value) if row else 1.0
    except (ValueError, TypeError):
        return 1.0


def _calc_theo_flow_and_efficiency(s1: float, f1: float, input_factor: float):
    try:
        theo_flow = (s1 * input_factor) / 231
        efficiency = 0.0 if theo_flow == 0 else (f1 * 0.01 / theo_flow) * 100
        return round(theo_flow, 2), round(efficiency, 2)
    except Exception:
        return 0.0, 0.0


@router.get("/get_live_data")
def get_live_data(db: Session = Depends(get_db)):
    snapshot = data_store.latest.copy()
    input_factor = _get_input_factor(db)

    s1 = float(snapshot.get("s1", 0))
    f1 = float(snapshot.get("f1", 0))
    theo_flow, efficiency = _calc_theo_flow_and_efficiency(s1, f1, input_factor)

    return {
        **snapshot,
        "input_factor": input_factor,
        "theo_flow": theo_flow,
        "efficiency": efficiency,
    }


@router.get("/get_signal_data")
def get_signal_data(signal: str, db: Session = Depends(get_db)):
    signal = signal.strip().upper()
    col_name = SIGNAL_COLUMN_MAP.get(signal)
    if not col_name:
        raise HTTPException(status_code=400, detail=f"Unknown signal: {signal}")

    col = getattr(TestLog, col_name)
    rows = (
        db.query(TestLog.logged_at, col)
        .order_by(TestLog.logged_at.desc())
        .limit(100)
        .all()
    )

    return [{"timestamp": r[0].isoformat(), "value": r[1]} for r in rows]


@router.get("/get_csv_data")
def get_csv_data(db: Session = Depends(get_db)):
    rows = (
        db.query(TestLog)
        .order_by(TestLog.logged_at.desc())
        .limit(20)
        .all()
    )

    data = []
    for r in rows:
        data.append({
            "Date": r.logged_at.strftime("%Y-%m-%d"),
            "Time": r.logged_at.strftime("%H:%M:%S"),
            "S1": r.s1, "SP": r.sp, "TP": r.tp,
            "Cycle": r.cycle, "Cycle Timer": r.cycle_timer,
            "LCSetpoint": r.lc_setpoint, "LC Regulate": r.lc_regulate,
            "Step": r.step,
            "F1": r.f1, "F2": r.f2, "F3": r.f3,
            "T1": r.t1, "T3": r.t3,
            "P1": r.p1, "P2": r.p2, "P3": r.p3, "P4": r.p4, "P5": r.p5,
        })

    return {"data": data}
