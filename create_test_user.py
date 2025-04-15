from sqlmodel import Session
from models import User
from database import engine
from datetime import datetime

def create_test_user():
    with Session(engine) as session:
        existing = session.exec(
            User.select().where(User.email == "student@example.com")
        ).first()
        if existing:
            print("ℹ️ Пользователь уже существует")
            return

        user = User(
            active=True,
            name="Тестовый Студент",
            email="student@example.com",
            phone="0000000000",
            created=datetime.utcnow(),
            card_id="123456789",
            user_type=1,  # Студент (из справочника UserType)
            email_verified=True,
            telegram_id=123456789,
            password="1234"
        )
        session.add(user)
        session.commit()
        print("Пользователь создан")

if __name__ == "__main__":
    create_test_user()