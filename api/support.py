from fastapi import APIRouter, Depends, HTTPException, status, Request as FastAPIRequest
from sqlmodel import Session
from api.auth import get_current_user
from database import engine
from models import User
from utils.email_sender import send_support_message

router = APIRouter(prefix="/support", tags=["Support"])

@router.post("/", response_model=dict)
def send_support_request(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    user_email = current_user.email
    message = data.get("message")

    if not message:
        raise HTTPException(status_code=400, detail="Пустое сообщение обращения")

    try:
        send_support_message(user_email, message)
        return {"message": "Обращение успешно отправлено"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Не удалось отправить обращение: {str(e)}"
        )
