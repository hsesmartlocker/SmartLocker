from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from starlette.config import Config
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import HTMLResponse
from authlib.integrations.starlette_client import OAuth
from sqlmodel import Session, select
from database import get_session
from models import User
import os

router = APIRouter()

# Настройка конфигурации
config = Config(".env")

CLIENT_ID = "19230-prj"
CLIENT_SECRET = os.environ.get("HSE_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:8000/auth/callback"  # измени на проде

oauth = OAuth(config)
oauth.register(
    name='hse',
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    server_metadata_url="https://profile.miem.hse.ru/auth/realms/MIEM/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"}
)


@router.get("/login-hse")
async def login(request: Request):
    redirect_uri = REDIRECT_URI
    return await oauth.hse.authorize_redirect(request, redirect_uri)


@router.get("/auth/callback")
async def auth_callback(request: Request, session: Session = Depends(get_session)):
    token = await oauth.hse.authorize_access_token(request)
    user_info = await oauth.hse.parse_id_token(request, token)

    # Падение, если id_token нет
    if not user_info:
        return HTMLResponse("<h1>Ошибка: не удалось получить данные пользователя</h1>", status_code=400)

    email = user_info.get("email")
    full_name = user_info.get("name")

    if not email:
        return HTMLResponse("<h1>Ошибка: email не найден</h1>", status_code=400)

    # Поиск пользователя в БД
    statement = select(User).where(User.email == email)
    result = session.exec(statement).first()

    if not result:
        # Создаём нового пользователя
        new_user = User(email=email, full_name=full_name)
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        result = new_user

    # Можно добавить генерацию JWT и редирект на фронт с ним
    return HTMLResponse(f"<h1>Добро пожаловать, {result.full_name}</h1><p>Email: {result.email}</p>")
