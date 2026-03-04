import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import AppSettings

router = APIRouter()
logger = logging.getLogger(__name__)

HEADER_FIELDS = [
    "programName", "description", "employeeId", "compSet",
    "inputFactor", "inputFactorType", "serialNumber", "customerId",
]


class HeaderData(BaseModel):
    programName: str
    description: str
    compSet: int
    inputFactor: float
    inputFactorType: str
    serialNumber: int
    employeeId: int
    customerId: int


@router.get("/get_header_data")
def get_header_data(db: Session = Depends(get_db)):
    rows = db.query(AppSettings).all()
    return {r.key: r.value for r in rows}


@router.post("/update_header_data")
def update_header_data(data: HeaderData, db: Session = Depends(get_db)):
    if data.inputFactorType not in ("cu/in", "cu/cm"):
        raise HTTPException(status_code=400, detail="Invalid inputFactorType")

    updates = data.model_dump()
    for key, value in updates.items():
        row = db.query(AppSettings).filter(AppSettings.key == key).first()
        if row:
            row.value = str(value)
        else:
            db.add(AppSettings(key=key, value=str(value)))

    db.commit()
    return {"status": "success"}
