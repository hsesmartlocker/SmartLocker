from fastapi import APIRouter, Depends, HTTPException, status, Body
from api.auth import get_current_user
from models import User
from utils.email_sender import send_support_message
from pydantic import BaseModel, EmailStr


class SupportRequest(BaseModel):
    message: str


router = APIRouter(prefix="/support", tags=["Support"])


@router.post("", response_model=dict)
def send_support_request(
        support_data: SupportRequest,
        current_user: User = Depends(get_current_user)
):
    message = support_data.message
    user_email = current_user.email

    print(f"[support] Получено обращение от {user_email}: {message}")

    try:
        send_support_message(user_email, message)
        return {"message": "Обращение успешно отправлено"}
    except Exception as e:
        print(f"[support error] {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Не удалось отправить обращение: {str(e)}"
        )


class AnonymousSupportRequest(BaseModel):
    name: str
    email: EmailStr
    message: str


@router.post("/anonymous", response_model=dict)
def send_anonymous_support_request(data: AnonymousSupportRequest):
    try:
        message_body = f"""
Имя: {data.name}
Почта: {data.email}

Сообщение:
{data.message}
"""
        send_support_message(data.email, message_body)
        return {"message": "Обращение успешно отправлено"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Не удалось отправить обращение: {str(e)}"
        )
