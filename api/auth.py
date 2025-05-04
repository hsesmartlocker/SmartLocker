from fastapi import APIRouter, HTTPException, Depends, status, requests
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlmodel import Session, select
from models import User, RegistrationCode
from database import get_session, engine
from jose import JWTError, jwt
from datetime import datetime, timedelta
import random
import string
from utils.email_sender import send_confirmation_email, send_temporary_password_email
from passlib.context import CryptContext

router = APIRouter(prefix="/auth", tags=["Auth"])

# Конфигурации
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "smartlocker-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


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


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ========================
# АВТОРИЗАЦИЯ
# ========================
@router.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


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