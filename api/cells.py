from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from models import Cell
from database import get_session

router = APIRouter(prefix="/cells", tags=["Cells"])

# Получить все свободные ячейки
@router.get("/available")
def get_available_cells(session: Session = Depends(get_session)):
    return session.exec(select(Cell).where(Cell.is_free == True)).all()
