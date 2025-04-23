from fastapi import APIRouter, Depends, HTTPException, status, Body
from api.auth import get_current_user
from models import User
from utils.email_sender import send_support_message
from pydantic import BaseModel


class SupportRequest(BaseModel):
    message: str

router = APIRouter(prefix="/support", tags=["Support"])

@router.post("/", response_model=dict)
def send_support_request(
    support_data: SupportRequest,
    current_user: User = Depends(get_current_user)
):
    message = support_data.message
    user_email = current_user.email

    print(f"[support] Получено обращение от {user_email}: {message}")  # <--- ВАЖНО

    try:
        send_support_message(user_email, message)
        return {"message": "Обращение успешно отправлено"}
    except Exception as e:
        print(f"[support error] {e}")  # <--- ВАЖНО
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Не удалось отправить обращение: {str(e)}"
        )
