from fastapi import APIRouter, HTTPException, Depends, status, requests
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
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

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
    name: str


class ResetPasswordRequest(BaseModel):
    old_password: str
    new_password: str


class AuthException(Exception):
    def __init__(self, detail: str, status_code: int = status.HTTP_401_UNAUTHORIZED):
        self.detail = detail
        self.status_code = status_code


class ConfirmResetData(BaseModel):
    email: str
    code: str


# ========================
# Утилиты
# ========================
def get_user_by_email(session: Session, email: str):
    return session.exec(select(User).where(User.email == email)).first()


def authenticate_user(email: str, password: str):
    with Session(engine) as session:
        user = get_user_by_email(session, email)
        if not user:
            raise AuthException(detail="Пользователь с таким email не найден")

        if not pwd_context.verify(password, user.password):
            raise AuthException(detail="Неверный пароль")

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
    try:
        user = authenticate_user(form_data.username, form_data.password)
    except AuthException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

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
        name=data.name,
        active=True,
        email_verified=True,
        user_type=user_type
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


@router.post("/reset-password/send-code")
def send_reset_code(email: EmailStr):
    code = ''.join(random.choices(string.digits, k=6))

    # Сохраняем в базу
    with Session(engine) as session:
        existing = session.exec(
            select(RegistrationCode).where(RegistrationCode.email == email)
        ).first()
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
        record = session.exec(
            select(RegistrationCode).where(RegistrationCode.email == data.email)
        ).first()

        if not record or record.code != data.code:
            raise HTTPException(status_code=400, detail="Неверный код")

        user = session.exec(
            select(User).where(User.email == data.email)
        ).first()

        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        user.password = get_password_hash(new_password)
        session.delete(record)
        session.commit()

        send_temporary_password_email(data.email, new_password)

        return {"message": "Новый пароль отправлен на почту"}


@router.post("hse/token")
async def login_with_hse_code(code: str, db: Session = Depends(get_session)):
    # 1. Отправляем code в токен-эндпоинт напрямую
    response = requests.post("https://profile.miem.hse.ru/auth/realms/MIEM/protocol/openid-connect/token", data={
        "grant_type": "authorization_code",
        "code": code,
        "client_id": "19230-prj",
        "redirect_uri": "https://1789.nas.helow19274.ru/auth/callback",
        "client_secret": "твой_секрет",
    })

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Ошибка при получении токена")

    access_token = response.json().get("access_token")

    # 2. Получаем userinfo
    userinfo = requests.get(
        "https://profile.miem.hse.ru/auth/realms/MIEM/protocol/openid-connect/userinfo",
        headers={"Authorization": f"Bearer {access_token}"}
    ).json()

    email = userinfo.get("email") or userinfo.get("email_hse")
    if not email:
        raise HTTPException(status_code=400, detail="Email не найден")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # 3. Выдаём JWT как обычно
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token}
