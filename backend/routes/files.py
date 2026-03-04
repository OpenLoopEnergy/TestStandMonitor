import logging
import os
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()
logger = logging.getLogger(__name__)

EXPORT_DIR = os.getenv("EXPORT_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "exports"))
BACKUP_DIR = os.path.join(EXPORT_DIR, "db_backups")


def _safe_path(directory: str, filename: str) -> str:
    """Resolve a filename inside a directory, rejecting traversal attempts."""
    if ".." in filename or filename.startswith("/") or filename.startswith("\\"):
        raise HTTPException(status_code=400, detail="Invalid filename")
    full = os.path.realpath(os.path.join(directory, filename))
    if not full.startswith(os.path.realpath(directory)):
        raise HTTPException(status_code=400, detail="Invalid filename")
    return full


def _find_file(filename: str) -> str:
    """Find a file in EXPORT_DIR or BACKUP_DIR."""
    for directory in (EXPORT_DIR, BACKUP_DIR):
        try:
            path = _safe_path(directory, filename)
            if os.path.isfile(path):
                return path
        except HTTPException:
            pass
    raise HTTPException(status_code=404, detail="File not found")


@router.get("/past_tests")
def past_tests():
    os.makedirs(EXPORT_DIR, exist_ok=True)

    xlsx_files = []
    for f in os.listdir(EXPORT_DIR):
        if f.lower().endswith(".xlsx"):
            full = os.path.join(EXPORT_DIR, f)
            mod = os.path.getmtime(full)
            xlsx_files.append({
                "filename": f,
                "modified_time": datetime.fromtimestamp(mod).strftime("%B %d, %Y at %I:%M:%S %p"),
            })
    xlsx_files.sort(key=lambda x: x["modified_time"], reverse=True)

    db_files = []
    if os.path.isdir(BACKUP_DIR):
        for f in os.listdir(BACKUP_DIR):
            if f.lower().endswith(".db"):
                full = os.path.join(BACKUP_DIR, f)
                mod = os.path.getmtime(full)
                db_files.append({
                    "filename": f,
                    "modified_time": datetime.fromtimestamp(mod).strftime("%B %d, %Y at %I:%M:%S %p"),
                })
        db_files.sort(key=lambda x: x["modified_time"], reverse=True)

    return {"files": xlsx_files, "db_files": db_files}


@router.get("/download_test/{filename}")
def download_test(filename: str):
    path = _find_file(filename)
    if filename.lower().endswith(".xlsx"):
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        media_type = "application/octet-stream"
    return FileResponse(path, media_type=media_type, filename=filename)


@router.delete("/delete_file/{filename}")
def delete_file(filename: str):
    path = _find_file(filename)
    try:
        os.remove(path)
        return {"status": "success", "message": "File deleted."}
    except Exception as e:
        logger.error("Error deleting %s: %s", filename, e)
        raise HTTPException(status_code=500, detail="Failed to delete file.")
