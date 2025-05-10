from fastapi import APIRouter, HTTPException, Depends, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr
from sqlmodel import Session, select
from models import User, RegistrationCode
from database import get_session, engine
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import random
import string
from utils.email_sender import send_confirmation_email, send_temporary_password_email
from passlib.context import CryptContext
import httpx
import os

ACCESS_SECRET_KEY = os.getenv("SECRET_KEY")
REFRESH_SECRET_KEY = os.getenv("REFRESH_SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 45))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 30))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "smartlocker-secret-key"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

CLIENT_ID = "19230-prj"
CLIENT_SECRET = os.getenv("HSE_CLIENT_SECRET")
REDIRECT_URI = "smartlocker://auth/callback"
TOKEN_URL = "https://profile.miem.hse.ru/auth/realms/MIEM/protocol/openid-connect/token"
USERINFO_URL = "https://profile.miem.hse.ru/auth/realms/MIEM/protocol/openid-connect/userinfo"

router = APIRouter(prefix="/auth", tags=["Auth"])


# ========================
# МОДЕЛИ
# ========================
class Token(BaseModel):
    access_token: str
    token_type: str


class ConfirmData(BaseModel):
    email: str
    code: str
    password: str
    name: str


class ConfirmResetData(BaseModel):
    email: str
    code: str


class ResetPasswordRequest(BaseModel):
    old_password: str
    new_password: str


class ResetPasswordSimpleRequest(BaseModel):
    email: str


class TokenRequest(BaseModel):
    code: str


# ========================
# УТИЛИТЫ
# ========================
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_user_by_email(session: Session, email: str):
    return session.exec(select(User).where(User.email == email)).first()


def authenticate_user(email: str, password: str):
    with Session(engine) as session:
        user = get_user_by_email(session, email)
        if not user:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
        if not verify_password(password, user.password):
            raise HTTPException(status_code=401, detail="Неверный пароль")
        return user


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, ACCESS_SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, REFRESH_SECRET_KEY, algorithm=ALGORITHM)


# ========================
# АВТОРИЗАЦИЯ
# ========================
@router.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    access_token = create_access_token(data={"sub": user.email})
    return {
        "access_token": create_access_token({"sub": user.email}),
        "refresh_token": create_refresh_token({"sub": user.email}),
        "token_type": "bearer"
    }


@router.post("/refresh")
def refresh_token(refresh_token: str = Body(...)):
    try:
        payload = jwt.decode(refresh_token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        new_access_token = create_access_token({"sub": email})
        return {"access_token": new_access_token, "token_type": "bearer"}

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@router.post("/exchange")
def exchange_token(data: TokenRequest, session: Session = Depends(get_session)):
    try:
        token_response = httpx.post(
            TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "authorization_code",
                "code": data.code,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uri": REDIRECT_URI,
            },
        )
        token_response.raise_for_status()
        token_data = token_response.json()
        hse_access_token = token_data["access_token"]
    except Exception as e:
        print("[exchange error]", e)
        raise HTTPException(status_code=400, detail="Ошибка получения токена от HSE")

    try:
        userinfo_res = httpx.get(
            USERINFO_URL,
            headers={"Authorization": f"Bearer {hse_access_token}"},
        )
        userinfo_res.raise_for_status()
        userinfo = userinfo_res.json()
        email = userinfo.get("email")
        name = userinfo.get("name") or userinfo.get("preferred_username") or "Без имени"
        if not email:
            raise HTTPException(status_code=400, detail="Email не найден в userinfo")

        email_prefix = email.split("@")[0]

        user = session.exec(
            select(User).where(User.email.startswith(email_prefix))
        ).first()

        if not user:
            user_type = 1 if email.endswith("@edu.hse.ru") else 2 if email.endswith("@hse.ru") else 0
            user = User(
                email=email,
                name=name,
                password=get_password_hash('default-password'),  # временный
                active=True,
                email_verified=True,
                user_type=user_type
            )
            session.add(user)
            session.commit()

        access_token = create_access_token(data={"sub": user.email})
        return {
            "access_token": create_access_token({"sub": user.email}),
            "refresh_token": create_refresh_token({"sub": user.email}),
            "token_type": "bearer"
        }

    except Exception as e:
        print("[userinfo error]", e)
        raise HTTPException(status_code=400, detail="Ошибка получения данных пользователя")


@router.get("/done", response_class=HTMLResponse)
def auth_done(token: Optional[str] = None):
    if not token:
        return HTMLResponse("<h2>Ошибка: токен не найден</h2>", status_code=400)

    html = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
      <meta charset="UTF-8" />
      <title>Авторизация завершена</title>
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <style>
        body {{
          font-family: sans-serif;
          text-align: center;
          padding: 40px;
        }}
      </style>
    </head>
    <body>
      <h2>Завершаем вход...</h2>
      <p>Подождите, идет перенаправление</p>

      <script>
        const token = "{token}";
        localStorage.setItem("smartlocker_token", token);

        window.location.href = "smartlocker://callback?token=" + token;
      </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


# ========================
# ТЕКУЩИЙ ПОЛЬЗОВАТЕЛЬ
# ========================
def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Недействительный токен")
    except JWTError:
        raise HTTPException(status_code=401, detail="Недействительный токен")

    with Session(engine) as session:
        user = get_user_by_email(session, email)
        if not user:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
        return user


@router.get("/me")
def read_users_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "user_type": current_user.user_type
    }


# ========================
# РЕГИСТРАЦИЯ
# ========================
@router.post("/send-code")
def send_code(email: str, session: Session = Depends(get_session)):
    code = ''.join(random.choices(string.digits, k=6))
    existing = session.exec(select(RegistrationCode).where(RegistrationCode.email == email)).first()
    if existing:
        session.delete(existing)
        session.commit()

    session.add(RegistrationCode(email=email, code=code))
    session.commit()

    try:
        send_confirmation_email(email, code)
    except Exception:
        raise HTTPException(status_code=500, detail="Ошибка при отправке письма")

    return {"message": "Код отправлен на почту"}


@router.post("/confirm-code")
def confirm_code(data: ConfirmData, session: Session = Depends(get_session)):
    code_entry = session.exec(select(RegistrationCode).where(RegistrationCode.email == data.email)).first()

    if not code_entry or code_entry.code != data.code:
        raise HTTPException(status_code=400, detail="Неверный код")

    if session.exec(select(User).where(User.email == data.email)).first():
        raise HTTPException(status_code=400, detail="Пользователь уже существует")

    user_type = 1 if data.email.endswith('@edu.hse.ru') else 2 if data.email.endswith('@hse.ru') else 0

    session.add(User(
        email=data.email,
        password=get_password_hash(data.password),
        name=data.name,
        active=True,
        email_verified=True,
        user_type=user_type
    ))

    session.delete(code_entry)
    session.commit()

    access_token = create_access_token(data={"sub": data.email})
    return {"access_token": access_token, "token_type": "bearer"}


# ========================
# СМЕНА ПАРОЛЯ (авторизованный)
# ========================
@router.post("/reset-password")
def reset_password(
        data: ResetPasswordRequest,
        session: Session = Depends(get_session),
        current_user: User = Depends(get_current_user)
):
    user = session.exec(select(User).where(User.email == current_user.email)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    if not verify_password(data.old_password, user.password):
        raise HTTPException(status_code=400, detail="Неверный текущий пароль")

    user.password = get_password_hash(data.new_password)
    session.add(user)
    session.commit()

    return {"message": "Пароль успешно обновлён"}


# ========================
# ПРОСТОЙ СБРОС ПАРОЛЯ
# ========================
@router.post("/reset-password-simple")
def reset_password_simple(data: ResetPasswordSimpleRequest, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == data.email)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    user.password = get_password_hash(new_password)
    session.add(user)
    session.commit()

    try:
        send_temporary_password_email(data.email, new_password)
    except Exception as e:
        print(f"[email error] {e}")
        raise HTTPException(status_code=500, detail="Ошибка при отправке письма")

    return {"message": "Новый пароль отправлен на почту"}


# ========================
# ВОССТАНОВЛЕНИЕ ПО КОДУ
# ========================
@router.post("/reset-password/send-code")
def send_reset_code(email: EmailStr):
    code = ''.join(random.choices(string.digits, k=6))

    with Session(engine) as session:
        existing = session.exec(select(RegistrationCode).where(RegistrationCode.email == email)).first()
        if existing:
            existing.code = code
        else:
            session.add(RegistrationCode(email=email, code=code))
        session.commit()

    send_confirmation_email(email, code)
    return {"message": "Код отправлен на почту"}


@router.post("/reset-password/confirm-code")
def confirm_reset_code(data: ConfirmResetData):
    with Session(engine) as session:
        record = session.exec(select(RegistrationCode).where(RegistrationCode.email == data.email)).first()

        if not record or record.code != data.code:
            raise HTTPException(status_code=400, detail="Неверный код")

        user = session.exec(select(User).where(User.email == data.email)).first()
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        user.password = get_password_hash(new_password)
        session.delete(record)
        session.commit()

        send_temporary_password_email(data.email, new_password)

        return {"message": "Новый пароль отправлен на почту"}
