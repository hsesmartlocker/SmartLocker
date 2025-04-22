from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from models import Request, Item, RequestStatus, User
from database import engine
from api.auth import get_current_user
from datetime import datetime
from pydantic import BaseModel

router = APIRouter(prefix="/requests", tags=["Requests"])


class RequestCreate(BaseModel):
    item_id: int
    comment: str = "Автоматическое бронирование"
    planned_return_date: datetime


@router.post("/", response_model=dict)
def create_request(data: RequestCreate, current_user: User = Depends(get_current_user)):
    with Session(engine) as session:
        item = session.get(Item, data.item_id)
        if not item or not item.available:
            raise HTTPException(status_code=400, detail="Оборудование недоступно")

        # Определяем статус заявки
        status_name = (
            "Ожидает получение" if item.access_level == 1 else "На рассмотрении"
        )
        status = session.exec(
            select(RequestStatus).where(RequestStatus.name == status_name)
        ).first()
        if not status:
            raise HTTPException(
                status_code=400, detail=f"Не найден статус '{status_name}'"
            )

        # Создаём заявку
        request = Request(
            status=status.id,
            user=current_user.id,
            issued_by=current_user.id,
            created=datetime.utcnow(),
            comment=data.comment,
            planned_return_date=data.planned_return_date,
            item_id=data.item_id,
        )
        session.add(request)

        # Обновляем оборудование
        item.available = False
        session.add(item)

        session.commit()
        return {"message": "Заявка успешно создана"}


@router.get("/my")
def get_my_requests(current_user: User = Depends(get_current_user)):
    with Session(engine) as session:
        requests = session.exec(
            select(Request).where(Request.user == current_user.id).order_by(Request.created.desc())
        ).all()

        result = []
        for req in requests:
            item = session.get(Item, req.item_id)
            status = session.get(RequestStatus, req.status)
            result.append({
                "id": req.id,
                "item_name": item.name if item else "Оборудование",
                "status": status.name if status else "Неизвестно",
                "planned_return_date": req.planned_return_date.strftime('%Y-%m-%d') if req.planned_return_date else None,
            })
        return result
