from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from models import Request, RequestStatus, User, Item
from database import engine
from api.auth import get_current_user
from datetime import datetime
from pydantic import BaseModel

router = APIRouter(prefix="/requests", tags=["Requests"])


class RequestCreate(BaseModel):
    takendate: datetime
    planned_return_date: datetime
    comment: str = ""


@router.post("/")
def create_request(request_data: RequestCreate, current_user: User = Depends(get_current_user)):
    with Session(engine) as session:
        status = session.exec(select(RequestStatus).where(RequestStatus.name == "Ожидание")).first()
        if not status:
            raise HTTPException(status_code=400, detail="Default status 'Ожидание' not found")

        request = Request(
            status=status.id,
            user=current_user.id,
            issued_by=current_user.id,
            created=datetime.utcnow(),
            takendate=request_data.takendate,
            planned_return_date=request_data.planned_return_date,
            return_date=None,
            comment=request_data.comment
        )
        session.add(request)
        session.commit()
        session.refresh(request)
        return request


@router.get("/my")
def get_my_active_requests(current_user: User = Depends(get_current_user)):
    with Session(engine) as session:
        requests = session.exec(
            select(Request)
            .where(Request.user == current_user.id)
            .order_by(Request.created.desc())
        ).all()

        active_requests = []
        for req in requests:
            item = session.exec(select(Item).where(Item.status == req.status, Item.available == True)).first()
            if item:
                active_requests.append({
                    "id": req.id,
                    "item_name": item.name,
                    "planned_return_date": req.planned_return_date.strftime('%Y-%m-%d')
                })
        return active_requests

