import logging

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import ExportedFile

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/past_tests")
def past_tests(db: Session = Depends(get_db)):
    rows = db.query(ExportedFile).order_by(ExportedFile.created_at.desc()).all()
    files = [{"filename": r.filename, "created_at": r.created_at.isoformat()} for r in rows]
    return {"files": files, "db_files": []}


@router.get("/download_test/{filename}")
def download_test(filename: str, db: Session = Depends(get_db)):
    row = db.query(ExportedFile).filter(ExportedFile.filename == filename).first()
    if not row:
        raise HTTPException(status_code=404, detail="File not found")
    return Response(
        content=row.file_data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/delete_file/{filename}")
def delete_file(filename: str, db: Session = Depends(get_db)):
    row = db.query(ExportedFile).filter(ExportedFile.filename == filename).first()
    if not row:
        raise HTTPException(status_code=404, detail="File not found")
    db.delete(row)
    db.commit()
    return {"status": "success", "message": "File deleted."}


class RenameRequest(BaseModel):
    old_filename: str
    new_filename: str


@router.post("/rename_file")
def rename_file(body: RenameRequest, db: Session = Depends(get_db)):
    new_name = body.new_filename.strip()
    if not new_name.endswith(".xlsx"):
        new_name += ".xlsx"
    row = db.query(ExportedFile).filter(ExportedFile.filename == body.old_filename).first()
    if not row:
        raise HTTPException(status_code=404, detail="File not found")
    row.filename = new_name
    db.commit()
    return {"filename": row.filename}
