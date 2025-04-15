from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from models import Request, Item, ItemStatus, RequestStatus, User, RequestGroup, Group
from database import engine
from api.auth import get_current_user
from datetime import datetime

router = APIRouter(prefix="/return", tags=["Return"])

@router.post("/{request_id}")
def return_items(request_id: int, current_user: User = Depends(get_current_user)):
    with Session(engine) as session:
        # Получаем заявку
        request = session.get(Request, request_id)
        if not request:
            raise HTTPException(status_code=404, detail="Request not found")

        if request.user != current_user.id:
            raise HTTPException(status_code=403, detail="You are not the owner of this request")

        # Обновим статус заявки
        status_returned = session.exec(select(RequestStatus).where(RequestStatus.name == "Завершено")).first()
        if not status_returned:
            raise HTTPException(status_code=400, detail="Status 'Завершено' not found")

        request.status = status_returned.id
        request.return_date = datetime.utcnow()
        session.add(request)

        # Получаем группы, связанные с заявкой
        request_groups = session.exec(select(RequestGroup).where(RequestGroup.request == request_id)).all()
        group_ids = [rg.group for rg in request_groups]

        # Получаем все предметы из этих групп
        items = session.exec(select(Item).where(Item.group.in_(group_ids))).all()

        status_free = session.exec(select(ItemStatus).where(ItemStatus.name == "Свободен")).first()
        if not status_free:
            raise HTTPException(status_code=400, detail="Item status 'Свободен' not found")

        for item in items:
            item.status = status_free.id
            item.available = True
            session.add(item)

        session.commit()
        return {"message": "Оборудование успешно возвращено", "returned_items": len(items)}
