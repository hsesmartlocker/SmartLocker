from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, constr
from sqlmodel import Session, select
from models import User, RegistrationCode
from database import get_session, engine
from jose import JWTError, jwt
from datetime import datetime, timedelta
import random
import string
from utils.email_sender import send_confirmation_email, send_temporary_password_email


router = APIRouter(prefix="/auth", tags=["Auth"])

# JWT конфигурация
SECRET_KEY = "smartlocker-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


# ========================
# Pydantic модели
# ========================
class Token(BaseModel):
    access_token: str
    token_type: str


class ConfirmData(BaseModel):
    email: str
    code: str
    password: str


class ResetPasswordRequest(BaseModel):
    old_password: str
    new_password: str


# ========================
# Утилиты
# ========================
def get_user_by_email(session: Session, email: str):
    return session.exec(select(User).where(User.email == email)).first()


def authenticate_user(email: str, password: str):
    with Session(engine) as session:
        user = get_user_by_email(session, email)
        if not user or user.password != password:
            return None
        return user


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ========================
# Авторизация
# ========================
@router.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


# ========================
# Получить текущего пользователя
# ========================
def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить токен",
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    with Session(engine) as session:
        user = get_user_by_email(session, email)
        if not user:
            raise credentials_exception
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
# Отправка кода на email
# ========================
@router.post("/send-code")
def send_code(email: str, session: Session = Depends(get_session)):
    code = ''.join(random.choices(string.digits, k=6))

    existing = session.exec(select(RegistrationCode).where(RegistrationCode.email == email)).first()
    if existing:
        session.delete(existing)
        session.commit()

    new_code = RegistrationCode(email=email, code=code)
    session.add(new_code)
    session.commit()

    try:
        send_confirmation_email(email, code)
    except Exception:
        raise HTTPException(status_code=500, detail="Не удалось отправить письмо")

    return {"message": "Код отправлен на почту"}


# ========================
# Подтверждение кода и регистрация
# ========================
@router.post("/confirm-code")
def confirm_code(data: ConfirmData, session: Session = Depends(get_session)):
    result = session.exec(
        select(RegistrationCode).where(RegistrationCode.email == data.email)
    ).first()

    if not result or result.code != data.code:
        raise HTTPException(status_code=400, detail="Неверный код")

    user_exists = session.exec(select(User).where(User.email == data.email)).first()
    if user_exists:
        raise HTTPException(status_code=400, detail="Пользователь уже существует")

    # Определяем тип пользователя по почте
    if data.email.endswith('@edu.hse.ru'):
        user_type = 1  # студент
    elif data.email.endswith('@hse.ru'):
        user_type = 2  # сотрудник
    else:
        user_type = 0  # другой (по желанию, можно и исключение кидать)

    new_user = User(
        email=data.email,
        password=data.password,
        active=True,
        email_verified=True,
        user_type=user_type  # <- добавлено
    )

    session.add(new_user)
    session.delete(result)
    session.commit()

    return {"message": "Регистрация завершена"}


# ========================
# Смена пароля (авторизованный пользователь)
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

    if user.password != data.old_password:
        raise HTTPException(status_code=400, detail="Неверный пароль")

    user.password = data.new_password
    session.add(user)
    session.commit()

    return {"message": "Пароль успешно обновлён"}


class ResetPasswordSimpleRequest(BaseModel):
    email: str

@router.post("/reset-password-simple")
def reset_password_simple(
    data: ResetPasswordSimpleRequest,
    session: Session = Depends(get_session)
):
    email = data.email
    user = session.exec(select(User).where(User.email == email)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Генерируем новый пароль
    new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    user.password = new_password
    session.add(user)
    session.commit()

    try:
        send_temporary_password_email(email, new_password)
    except Exception as e:
        print(f"[email error] {e}")
        raise HTTPException(status_code=500, detail="Ошибка при отправке письма")

    return {"message": "Новый пароль отправлен на почту"}

@router.post("/hse-login")
async def hse_login_via_email(payload: dict, session: Session = Depends(get_session)):
    email = payload.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    user = session.exec(select(User).where(User.email == email)).first()
    if not user:
        # можно создать пользователя
        user = User(email=email, user_type=1)
        session.add(user)
        session.commit()
        session.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token}
