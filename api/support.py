from fastapi import APIRouter, Depends, HTTPException, status, Request
from api.auth import get_current_user
from models import User
from utils.email_sender import send_support_message

router = APIRouter(prefix="/support", tags=["Support"])

@router.post("/")
async def send_support_request(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    data = await request.json()
    message = data.get("message")

    if not message or not message.strip():
        raise HTTPException(status_code=400, detail="Пустое сообщение обращения")

    # Пытаемся отправить письмо
    try:
        send_support_message(
            user_email=current_user.email,
            message=message
        )
    except Exception as e:
        print(f"[email error] Ошибка при отправке письма: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось отправить обращение"
        )

    return {"message": "Обращение успешно отправлено"}