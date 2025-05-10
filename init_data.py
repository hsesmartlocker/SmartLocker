from sqlmodel import Session
from database import engine
from models import RequestStatus, UserType, ItemStatus


def seed_data():
    with Session(engine) as session:
        # ItemStatus
        item_statuses = ["Свободен", "Выдан", "Сломан", "Забронирован"]
        for name in item_statuses:
            session.add(ItemStatus(name=name))

        # RequestStatus
        request_statuses = [
            "Создана",
            "Отклонена",
            "Ожидает получения",
            "Выдано",
            "Ожидает возврата",
            "Возвращено",
            "Просрочено",
            "Отменена"
        ]
        for name in request_statuses:
            session.add(RequestStatus(name=name))

        # UserType
        user_types = ["Студент", "Сотрудник", "Админ"]
        for name in user_types:
            session.add(UserType(name=name))

        session.commit()
        print("Начальные данные успешно добавлены.")


if __name__ == "__main__":
    seed_data()
