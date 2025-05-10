from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from models import Request, Item, ItemStatus, Cell
from database import engine, get_session
from api.auth import get_current_user
from typing import List
from pydantic import BaseModel

router = APIRouter(prefix="/items", tags=["Items"])


@router.get("/", response_model=List[Item])
def get_all_items(current_user=Depends(get_current_user)):
    with Session(engine) as session:
        return session.exec(select(Item)).all()


@router.get("/available", response_model=List[Item])
def get_available_items(
        session: Session = Depends(get_session),
        current_user=Depends(get_current_user)
):
    free_status = session.exec(
        select(ItemStatus).where(ItemStatus.name == "Свободен")
    ).first()
    if not free_status:
        raise HTTPException(status_code=400, detail="Item status 'Свободен' not found")

    active_item_ids = session.exec(
        select(Request.item_id).where(Request.return_date.is_(None))
    ).all()

    statement = select(Item).where(
        Item.status == free_status.id,
        Item.available == True
    )

    if active_item_ids:
        statement = statement.where(Item.id.notin_(active_item_ids))

    return session.exec(statement).all()


class AdminBookingRequest(BaseModel):
    item_id: int
    reason: str


@router.post("/delete")
def delete_item(data: dict, db: Session = Depends(get_session)):
    item_id = data.get("item_id")

    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Оборудование не найдено")

    active_status_ids = [1, 3, 4, 5, 7]

    active_request = (
        db.query(Request)
        .filter(Request.item_id == item_id, Request.status.in_(active_status_ids))
        .first()
    )

    if active_request:
        raise HTTPException(status_code=400, detail="Нельзя удалить: есть активная заявка")

    if item.cell:
        cell = db.query(Cell).filter(Cell.id == item.cell).first()
        if cell:
            cell.is_free = True

    db.delete(item)
    db.commit()
    return {"success": True}


@router.post("/broke")
def toggle_broken_item(data: dict, session: Session = Depends(get_session)):
    item_id = data.get("item_id")
    if not item_id:
        raise HTTPException(status_code=400, detail="Не указан ID предмета")

    item = session.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Предмет не найден")

    if item.status == 1:
        item.status = 3
        item.available = False
    elif item.status == 3:
        item.status = 1
        item.available = True
    else:
        raise HTTPException(status_code=400, detail="Нельзя изменить статус")

    session.add(item)
    session.commit()

    return {"message": "Статус обновлён", "status": item.status}


@router.post("/change_cell")
def change_cell(data: dict, db: Session = Depends(get_session)):
    item_id = data.get("item_id")
    new_cell_id = data.get("cell_id")

    item = db.query(Item).filter(Item.id == item_id).first()
    new_cell = db.query(Cell).filter(Cell.id == new_cell_id).first()

    if not item or not new_cell:
        raise HTTPException(status_code=404, detail="Предмет или ячейка не найдены")

    if not new_cell.is_free:
        raise HTTPException(status_code=400, detail="Ячейка уже занята")

    if item.cell:
        old_cell = db.query(Cell).filter(Cell.id == item.cell).first()
        if old_cell:
            old_cell.is_free = True

    item.cell = new_cell_id
    new_cell.is_free = False

    db.commit()
    return {"message": "Ячейка успешно обновлена"}


@router.post("/new")
def create_item(data: dict, db: Session = Depends(get_session)):
    required_fields = ['inv_key', 'name', 'status', 'owner', 'available', 'access_level', 'specifications']
    for field in required_fields:
        if field not in data:
            raise HTTPException(status_code=400, detail=f"Отсутствует поле {field}")

    cell_id = data.get("cell")
    if cell_id is not None:
        cell = db.get(Cell, cell_id)
        if not cell:
            raise HTTPException(status_code=404, detail="Ячейка не найдена")
        if not cell.is_free:
            raise HTTPException(status_code=400, detail="Ячейка занята")

    new_item = Item(**data)
    db.add(new_item)

    if cell_id is not None:
        cell.is_free = False

    db.commit()
    db.refresh(new_item)
    return {"success": True, "item_id": new_item.id}
