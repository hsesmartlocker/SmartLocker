from fastapi import APIRouter, Depends, HTTPException, Body
from sqlmodel import Session, select
from models import Request, Item, ItemStatus
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
