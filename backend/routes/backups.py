import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import DataBackup
from backend.routes.export import build_export, store_exported_file
from backend.services.data_backup import (
    load_backup_headers,
    load_backup_payload,
    update_backup_headers,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/data_backups")
def list_data_backups(db: Session = Depends(get_db)):
    rows = db.query(DataBackup).order_by(DataBackup.created_at.desc()).all()
    return {
        "backups": [
            {
                "id": b.id,
                "label": b.label,
                "created_at": b.created_at.isoformat(),
                "trigger": b.trigger,
                "row_count": b.row_count,
                "first_logged_at": b.first_logged_at.isoformat() if b.first_logged_at else None,
                "last_logged_at": b.last_logged_at.isoformat() if b.last_logged_at else None,
                "headers": load_backup_headers(b),
            }
            for b in rows
        ]
    }


class UpdateHeadersRequest(BaseModel):
    headers: dict


@router.post("/update_backup_headers/{backup_id}")
def update_headers(backup_id: int, body: UpdateHeadersRequest, db: Session = Depends(get_db)):
    """Edit the header snapshot (input factor, program name, etc.) for a backup so
    a re-export uses corrected values rather than whatever was captured on clear."""
    backup = db.query(DataBackup).filter(DataBackup.id == backup_id).first()
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")
    merged = update_backup_headers(db, backup, body.headers)
    return {"headers": merged}


@router.post("/export_backup/{backup_id}")
def export_backup(backup_id: int, db: Session = Depends(get_db)):
    """Re-export an old backup using the current export logic.

    Reconstructs the raw rows + metadata snapshot and runs them through the same
    builder as a live export, so the result reflects today's exportXLSX code.
    """
    backup = db.query(DataBackup).filter(DataBackup.id == backup_id).first()
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")

    row_dicts, headers, dir_switch_val = load_backup_payload(backup)
    if not row_dicts:
        raise HTTPException(status_code=404, detail="Backup contains no data to export.")

    try:
        excel_path = build_export(row_dicts, headers, dir_switch_val)
    except Exception as e:
        logger.error("Backup re-export failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    excel_filename = store_exported_file(db, excel_path)

    return FileResponse(
        excel_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=excel_filename,
    )


class RenameBackupRequest(BaseModel):
    label: str


@router.post("/rename_backup/{backup_id}")
def rename_backup(backup_id: int, body: RenameBackupRequest, db: Session = Depends(get_db)):
    backup = db.query(DataBackup).filter(DataBackup.id == backup_id).first()
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")
    new_label = body.label.strip()
    if not new_label:
        raise HTTPException(status_code=400, detail="Label cannot be empty.")
    backup.label = new_label
    db.commit()
    return {"label": backup.label}


@router.delete("/delete_backup/{backup_id}")
def delete_backup(backup_id: int, db: Session = Depends(get_db)):
    backup = db.query(DataBackup).filter(DataBackup.id == backup_id).first()
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")
    db.delete(backup)
    db.commit()
    return {"status": "success", "message": "Backup deleted."}
