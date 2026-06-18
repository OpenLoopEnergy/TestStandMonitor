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
from backend.services.data_backup import create_data_backup
from backend.time_utils import get_export_now

router = APIRouter()
logger = logging.getLogger(__name__)

HEADER_FIELDS_TOP = [
    ("programName", "Program Name"),
    ("description", "Description"),
    ("employeeId", "Employee ID"),
    ("compSet", "Comp Set"),
    ("inputFactor", "Input Factor"),
    ("inputFactorType", "Input Factor Type"),
]

HEADER_FIELDS_BOTTOM = [
    ("serialNumber", "Serial Number"),
    ("customerId", "Customer ID"),
]

_DIR_SWITCH_LABELS = {0: "Both", 1: "Forward", 2: "Backward"}


EXPORT_DIR = os.getenv("EXPORT_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "exports"))


def _get_setting(db: Session, key: str) -> str:
    row = db.query(AppSettings).filter(AppSettings.key == key).first()
    return row.value if row else "N/A"


def get_export_headers(db: Session) -> dict:
    """Read all metadata fields used in the export header from AppSettings."""
    all_header_fields = HEADER_FIELDS_TOP + HEADER_FIELDS_BOTTOM + [("minEfficiencyPct", "Min Efficiency %")]
    return {field_key: _get_setting(db, field_key) for field_key, _ in all_header_fields}


def build_export(row_dicts: list[dict], headers: dict, dir_switch_val) -> str:
    """Build the CSV from serialized rows + metadata, then convert to Excel.

    `row_dicts` come from `serialize_test_log_rows` (live export) or from a backup
    snapshot (re-export). Both paths share this single CSV/Excel builder so that
    re-exporting an old backup always uses the current export logic.

    Returns the path to the generated .xlsx file.
    """
    now = get_export_now()
    timestamp = now.strftime("(%m-%d-%Y_%I-%M-%S_%p)")
    csv_filename = f"{timestamp}_log_data.csv"

    os.makedirs(EXPORT_DIR, exist_ok=True)
    csv_path = os.path.join(EXPORT_DIR, csv_filename)

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Metadata rows
        for field_key, display_name in HEADER_FIELDS_TOP:
            writer.writerow([display_name, headers.get(field_key, "N/A")])
        writer.writerow(["Direction Switch", _DIR_SWITCH_LABELS.get(dir_switch_val, str(dir_switch_val))])
        for field_key, display_name in HEADER_FIELDS_BOTTOM:
            writer.writerow([display_name, headers.get(field_key, "N/A")])
        min_eff = headers.get("minEfficiencyPct", "")
        if min_eff and min_eff not in ("N/A", ""):
            try:
                writer.writerow(["Min Efficiency %", float(min_eff)])
            except ValueError:
                pass

        writer.writerow([])  # Blank separator

        # Column headers
        writer.writerow([
            "Date", "Time", "S1", "SP", "TP", "Cycle", "Cycle Timer",
            "LCSetpoint", "LC Regulate", "Step",
            "F1", "F2", "F3", "T1", "T3", "P1", "P2", "P3", "P4", "P5",
            "TP Reversed", "Trending",
        ])

        # Data rows — F1 scaled × 0.01 here (single place, same as original)
        for r in row_dicts:
            logged_at = datetime.fromisoformat(r["logged_at"]).astimezone(now.tzinfo)
            raw_f1 = r["f1"] if r.get("f1") is not None else 0.0
            scaled_f1 = raw_f1 * 0.01
            raw_f3 = r["f3"] if r.get("f3") is not None else 0.0
            scaled_f3 = raw_f3 * 0.01
            writer.writerow([
                logged_at.strftime("%Y-%m-%d"),
                logged_at.strftime("%H:%M:%S"),
                r.get("s1"), r.get("sp"), r.get("tp"),
                r.get("cycle"), r.get("cycle_timer"),
                r.get("lc_setpoint"), r.get("lc_regulate"),
                r.get("step"),
                f"{scaled_f1:.2f}", r.get("f2"), f"{scaled_f3:.2f}",
                r.get("t1"), r.get("t3"),
                r.get("p1"), r.get("p2"), r.get("p3"), r.get("p4"), r.get("p5"),
                1 if r.get("tp_reversed") else 0,
                r["trending"] if r.get("trending") is not None else 0,
            ])

    # Convert CSV → Excel using the preserved exportXLSX logic
    from backend.exportXLSX import process_csv_to_excel_from_file
    return process_csv_to_excel_from_file(csv_path)


def store_exported_file(db: Session, excel_path: str) -> str:
    """Persist the generated Excel file so all users see it on Past Tests, then
    upload to SharePoint. Returns the Excel filename.

    Guards against duplicates when multiple users export at the same time: if a
    file of the same size was saved in the last 30 seconds, skip the insert.
    """
    excel_filename = os.path.basename(excel_path)

    with open(excel_path, "rb") as fh:
        file_bytes = fh.read()
    from datetime import timedelta, timezone
    recent_cutoff = datetime.now(timezone.utc) - timedelta(seconds=30)
    recent = db.query(ExportedFile).filter(ExportedFile.created_at >= recent_cutoff).all()
    if not any(len(e.file_data) == len(file_bytes) for e in recent):
        db.add(ExportedFile(filename=excel_filename, file_data=file_bytes))
        db.commit()

    # Upload to SharePoint (no-ops silently if Azure env vars are not set)
    from backend.services.sharepoint_upload import upload_to_sharepoint
    upload_to_sharepoint(excel_path, excel_filename)

    return excel_filename


@router.post("/export_data")
def export_data(db: Session = Depends(get_db)):
    from backend.services.data_backup import serialize_test_log_rows

    headers = get_export_headers(db)

    # Fetch all logged rows (no limit — full test run)
    rows = db.query(TestLog).order_by(TestLog.logged_at.asc()).all()
    if not rows:
        raise HTTPException(status_code=404, detail="No data in CSV file to export.")

    row_dicts = serialize_test_log_rows(rows)
    dir_switch_val = data_store.latest.get("ee_dir_switch", 0)

    try:
        excel_path = build_export(row_dicts, headers, dir_switch_val)
    except Exception as e:
        logger.error("Excel export failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    excel_filename = store_exported_file(db, excel_path)

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


class LogManualRequest(BaseModel):
    enabled: bool


@router.post("/set_log_manual")
async def set_log_manual(body: LogManualRequest):
    data_store.log_manual = body.enabled
    await data_store.update({"log_manual": body.enabled})
    return {"log_manual": data_store.log_manual}


@router.post("/clear_data_table")
def clear_data_table(trigger: str = "manual", db: Session = Depends(get_db)):
    try:
        # Snapshot the data table into a backup before wiping it, so the raw data
        # can be re-exported later. Skip when the table is already empty.
        rows = db.query(TestLog).order_by(TestLog.logged_at.asc()).all()
        if rows:
            create_data_backup(db, rows, trigger, get_export_headers(db))
        db.query(TestLog).delete()
        db.commit()
        return {"status": "success", "message": "Data table cleared."}
    except Exception as e:
        db.rollback()
        logger.error("Failed to clear data table: %s", e)
        raise HTTPException(status_code=500, detail="Failed to clear data table.")
