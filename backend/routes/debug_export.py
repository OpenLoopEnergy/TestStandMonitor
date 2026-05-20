import logging
import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import AppSettings, DebugLog, ExportedFile
from backend.services import data_store
from backend.time_utils import get_export_now

router = APIRouter()
logger = logging.getLogger(__name__)

EXPORT_DIR = os.getenv("EXPORT_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "exports"))


def _get_setting(db: Session, key: str) -> str:
    row = db.query(AppSettings).filter(AppSettings.key == key).first()
    return row.value if row else ""


@router.post("/export_debug_data")
def export_debug_data(db: Session = Depends(get_db)):
    rows = db.query(DebugLog).order_by(DebugLog.logged_at.asc()).all()
    if not rows:
        raise HTTPException(status_code=404, detail="No debug log data to export.")

    metadata = {
        "programName":     _get_setting(db, "programName"),
        "description":     _get_setting(db, "description"),
        "employeeId":      _get_setting(db, "employeeId"),
        "compSet":         _get_setting(db, "compSet"),
        "inputFactor":     _get_setting(db, "inputFactor"),
        "inputFactorType": _get_setting(db, "inputFactorType"),
        "serialNumber":    _get_setting(db, "serialNumber"),
        "customerId":      _get_setting(db, "customerId"),
    }

    try:
        from backend.exportDebugXLSX import process_debug_to_excel
        excel_path = process_debug_to_excel(rows, metadata, EXPORT_DIR)
    except Exception as e:
        import traceback
        logger.error("Debug Excel export failed: %s\n%s", e, traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

    excel_filename = os.path.basename(excel_path)

    # Save to ExportedFile table so it appears in Past Tests
    with open(excel_path, "rb") as fh:
        file_bytes = fh.read()
    recent_cutoff = datetime.now(timezone.utc) - timedelta(seconds=30)
    recent = db.query(ExportedFile).filter(ExportedFile.created_at >= recent_cutoff).all()
    if not any(len(e.file_data) == len(file_bytes) for e in recent):
        db.add(ExportedFile(filename=excel_filename, file_data=file_bytes))
        db.commit()

    return FileResponse(
        excel_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=excel_filename,
    )


@router.post("/clear_debug_table")
async def clear_debug_table(db: Session = Depends(get_db)):
    try:
        db.query(DebugLog).delete()
        db.commit()
        # Reset the broadcast counter so the frontend sees 0 immediately
        await data_store.update({"debug_rows_logged": 0})
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        logger.error("Failed to clear debug table: %s", e)
        raise HTTPException(status_code=500, detail="Failed to clear debug table.")
