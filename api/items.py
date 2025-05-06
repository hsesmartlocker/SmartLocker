from fastapi import APIRouter, Depends, HTTPException, Body
from sqlmodel import Session, select
from models import Request, Item, ItemStatus, Cell
from database import engine, get_session
from api.auth import get_current_user
from typing import List
from pydantic import BaseModel
from utils.email_sender import send_admin_request_email

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


@router.post("/request-via-email")
def request_item_via_email(
    request: AdminBookingRequest,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user)
):
    item = session.exec(select(Item).where(Item.id == request.item_id)).first()
    if not item:
        raise HTTPException(status_code=404, detail="Оборудование не найдено")

    try:
        send_admin_request_email(
            user_email=current_user.email,
            equipment_name=item.name,
            reason=request.reason
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Не удалось отправить письмо: {str(e)}")

    return {"message": "Заявка успешно отправлена. Мы уведомим вас в течение 24 часов."}


@router.post("/items/delete")
def delete_item(data: dict, db: Session = Depends(get_session)):
    item_id = data.get("item_id")
    item = db.query(Item).filter(Item.id == item_id).first()

    if not item:
        raise HTTPException(status_code=404, detail="Предмет не найден")

    has_requests = db.query(Request).filter(Request.item_id == item_id, Request.status.in_(['создана', 'на рассмотрении', 'выдано', 'ожидает возврата'])).first()

    if has_requests:
        raise HTTPException(status_code=400, detail="Невозможно удалить: предмет используется в заявке")

    db.delete(item)
    db.commit()
    return {"success": True}


@router.post("/items/broke")
def toggle_broken_item(data: dict, db: Session = Depends(get_session)):
    item_id = data.get("item_id")
    item = db.query(Item).filter(Item.id == item_id).first()

    if not item:
        raise HTTPException(status_code=404, detail="Предмет не найден")

    # Статус: 1 — свободно, 3 — сломано
    if item.status == 1:
        item.status = 3
    elif item.status == 3:
        item.status = 1
    else:
        raise HTTPException(status_code=400, detail="Можно переключать только свободные или сломанные предметы")

    # Освобождаем ячейку
    if item.cell:
        item.cell.is_free = True
        item.cell_id = None

    db.commit()
    return {"success": True, "new_status": item.status}


@router.post("/items/change_cell")
def change_cell(data: dict, db: Session = Depends(get_session)):
    item_id = data.get("item_id")
    new_cell_id = data.get("cell_id")

    item = db.query(Item).filter(Item.id == item_id).first()
    new_cell = db.query(Cell).filter(Cell.id == new_cell_id).first()

    if not item or not new_cell:
        raise HTTPException(status_code=404, detail="Предмет или ячейка не найдены")

    if not new_cell.is_free:
        raise HTTPException(status_code=400, detail="Ячейка уже занята")

    # Освобождаем старую ячейку
    if item.cell:
        item.cell.is_free = True

    # Назначаем новую
    item.cell_id = new_cell_id
    new_cell.is_free = False

    db.commit()
    return {"success": True}
