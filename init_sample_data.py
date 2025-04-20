from sqlmodel import Session
from datetime import datetime

from database import engine
from models import (
    UserType, RequestStatus, ItemStatus,
    User, UserAccess, Item, Request
)

def populate_sample_data():
    with Session(engine) as session:
        # === Справочники ===
        student_type = UserType(name="Студент")
        staff_type = UserType(name="Сотрудник")
        session.add_all([student_type, staff_type])
        session.commit()

        status_waiting = RequestStatus(name="Ожидание")
        status_issued = RequestStatus(name="Выдано")
        status_returned = RequestStatus(name="Возвращено")
        status_closed = RequestStatus(name="Закрыта")
        session.add_all([status_waiting, status_issued, status_returned])
        session.commit()


        item_free = ItemStatus(name="Свободен")
        item_issued = ItemStatus(name="Выдан")
        item_broken = ItemStatus(name="Сломан")
        session.add_all([item_free, item_issued, item_broken])
        session.commit()


        # === Пользователи ===
        user = User(
            active=True,
            name="Иван Студент",
            email="student@example.com",
            phone="0000000000",
            created=datetime.utcnow(),
            card_id="123456789",
            user_type=student_type.id,
            email_verified=True,
            telegram_id=123456,
            password="1234"
        )
        session.add(user)
        session.commit()

        session.add(UserAccess(user=user.id))
        session.commit()

        # === Оборудование ===
        item = Item(
            inv_key="INV001",
            status=item_free.id,
            owner="МИЭМ",
            available=True,
            specifications={"Color": "Black"}
        )
        session.add(item)
        session.commit()

        request = Request(
            status=status_waiting.id,
            user=user.id,
            issued_by=user.id,
            comment="Тестовая заявка",
            created=datetime.utcnow(),
            takendate=datetime(2025, 4, 12, 10, 0),
            planned_return_date=datetime(2025, 4, 13, 10, 0),
            return_date=datetime(2025, 4, 13, 18, 0)
        )
        session.add(request)
        session.commit()

        print("База успешно заполнена тестовыми данными.")

if __name__ == "__main__":
    populate_sample_data()