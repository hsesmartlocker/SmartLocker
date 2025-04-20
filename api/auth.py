from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlmodel import Session, select
from models import User, RegistrationCode
from database import engine, get_session
from jose import JWTError, jwt
from datetime import datetime, timedelta
import random
import string
from utils.email_sender import send_confirmation_email

router = APIRouter(prefix="/auth", tags=["Auth"])

# Конфигурация токенов
SECRET_KEY = "smartlocker-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# ========================
# MODELS
# ========================
class Token(BaseModel):
    access_token: str
    token_type: str

class ConfirmData(BaseModel):
    email: str
    code: str
    password: str

# ========================
# AUTH FUNCTIONS
# ========================
def get_user_by_email(session: Session, email: str):
    statement = select(User).where(User.email == email)
    return session.exec(statement).first()

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
# LOGIN
# ========================
@router.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# ========================
# GET CURRENT USER
# ========================
def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    with Session(engine) as session:
        user = get_user_by_email(session, email)
        if user is None:
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
# REGISTRATION WITH CODE
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

    new_user = User(
        email=data.email,
        password=data.password,
        active=True,
        email_verified=True
    )
    session.add(new_user)
    session.delete(result)
    session.commit()

    return {"message": "Регистрация завершена"}
