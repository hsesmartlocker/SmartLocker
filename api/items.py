from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from models import Item, ItemStatus, Hardware
from database import engine
from api.auth import get_current_user
from typing import List

router = APIRouter(prefix="/items", tags=["Items"])

@router.get("/", response_model=List[Item])
def get_all_items(current_user=Depends(get_current_user)):
    with Session(engine) as session:
        return session.exec(select(Item)).all()

@router.get("/available", response_model=List[Item])
def get_available_items(current_user=Depends(get_current_user)):
    with Session(engine) as session:
        status = session.exec(select(ItemStatus).where(ItemStatus.name == "Свободен")).first()
        if not status:
            raise HTTPException(status_code=400, detail="Item status 'Свободен' not found")
        statement = select(Item).where(Item.status == status.id, Item.available == True)
        return session.exec(statement).all()

@router.get("/hardware/{hardware_id}", response_model=List[Item])
def get_items_by_hardware(hardware_id: int, current_user=Depends(get_current_user)):
    with Session(engine) as session:
        return session.exec(select(Item).where(Item.hardware == hardware_id)).all()
