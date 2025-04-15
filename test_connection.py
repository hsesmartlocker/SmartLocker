from sqlmodel import Session, select
from database import engine
from models import User

with Session(engine) as session:
    users = session.exec(select(User)).all()
    print(f"Подключение работает, пользователей в таблице: {len(users)}")
