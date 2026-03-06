import csv
import io
import logging
import os
import tempfile
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import TestLog, AppSettings, ExportedFile
from backend.services import data_store

router = APIRouter()
logger = logging.getLogger(__name__)

HEADER_FIELDS = [
    ("programName", "Program Name"),
    ("description", "Description"),
    ("employeeId", "Employee ID"),
    ("compSet", "Comp Set"),
    ("inputFactor", "Input Factor"),
    ("inputFactorType", "Input Factor Type"),
    ("serialNumber", "Serial Number"),
    ("customerId", "Customer ID"),
]

EXPORT_DIR = os.getenv("EXPORT_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "exports"))


def _get_setting(db: Session, key: str) -> str:
    row = db.query(AppSettings).filter(AppSettings.key == key).first()
    return row.value if row else "N/A"


@router.post("/export_data")
def export_data(db: Session = Depends(get_db)):
    # Fetch header metadata
    headers = {field_key: _get_setting(db, field_key) for field_key, _ in HEADER_FIELDS}

    # Fetch all logged rows (no limit — full test run)
    rows = db.query(TestLog).order_by(TestLog.logged_at.asc()).all()
    if not rows:
        raise HTTPException(status_code=404, detail="No data in CSV file to export.")

    # Build CSV in memory
    timestamp = datetime.now().strftime("(%Y-%m-%d_%H-%M-%S)")
    csv_filename = f"{timestamp}_log_data.csv"

    os.makedirs(EXPORT_DIR, exist_ok=True)
    csv_path = os.path.join(EXPORT_DIR, csv_filename)

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Metadata rows
        for field_key, display_name in HEADER_FIELDS:
            writer.writerow([display_name, headers.get(field_key, "N/A")])

        writer.writerow([])  # Blank separator

        # Column headers
        writer.writerow([
            "Date", "Time", "S1", "SP", "TP", "Cycle", "Cycle Timer",
            "LCSetpoint", "LC Regulate", "Step",
            "F1", "F2", "F3", "T1", "T3", "P1", "P2", "P3", "P4", "P5",
            "TP Reversed",
        ])

        # Data rows — F1 scaled × 0.01 here (single place, same as original)
        for r in rows:
            raw_f1 = r.f1 if r.f1 is not None else 0.0
            scaled_f1 = raw_f1 * 0.01
            writer.writerow([
                r.logged_at.strftime("%Y-%m-%d"),
                r.logged_at.strftime("%H:%M:%S"),
                r.s1, r.sp, r.tp,
                r.cycle, r.cycle_timer,
                r.lc_setpoint, r.lc_regulate,
                r.step,
                f"{scaled_f1:.2f}", r.f2, r.f3,
                r.t1, r.t3,
                r.p1, r.p2, r.p3, r.p4, r.p5,
                1 if r.tp_reversed else 0,
            ])

    # Convert CSV → Excel using the preserved exportXLSX logic
    try:
        from backend.exportXLSX import process_csv_to_excel_from_file
        excel_path = process_csv_to_excel_from_file(csv_path)
    except Exception as e:
        logger.error("Excel export failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    excel_filename = os.path.basename(excel_path)

    # Save to DB so all users can see it on Past Tests
    with open(excel_path, "rb") as fh:
        file_bytes = fh.read()
    db.add(ExportedFile(filename=excel_filename, file_data=file_bytes))
    db.commit()

    return FileResponse(
        excel_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=excel_filename,
    )


class DebugModeRequest(BaseModel):
    enabled: bool


@router.post("/set_debug_mode")
async def set_debug_mode(body: DebugModeRequest):
    data_store.debug_mode = body.enabled
    await data_store.update({"debug_mode": body.enabled})
    return {"debug_mode": data_store.debug_mode}


@router.post("/clear_data_table")
def clear_data_table(db: Session = Depends(get_db)):
    try:
        db.query(TestLog).delete()
        db.commit()
        return {"status": "success", "message": "Data table cleared."}
    except Exception as e:
        db.rollback()
        logger.error("Failed to clear data table: %s", e)
        raise HTTPException(status_code=500, detail="Failed to clear data table.")
