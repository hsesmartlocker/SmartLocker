from sqlmodel import Session
from database import engine
from models import RequestStatus, UserType, ItemStatus, GroupStatus, OperationType

def seed_data():
    with Session(engine) as session:
        # RequestStatus
        for name in ["Ожидание", "Выдано", "Завершено", "Отменено"]:
            session.add(RequestStatus(name=name))

        # UserType
        for name in ["Студент", "Преподаватель", "Сотрудник"]:
            session.add(UserType(name=name))

        # ItemStatus
        for name in ["Свободен", "Выдан", "В ремонте", "Утерян"]:
            session.add(ItemStatus(name=name))

        # GroupStatus
        for name in ["Готов", "Не готов", "Архив"]:
            session.add(GroupStatus(name=name))

        # OperationType
        for name in ["create", "update", "delete", "issue", "return"]:
            session.add(OperationType(name=name))

        session.commit()
        print("✅ Начальные данные успешно добавлены.")

if __name__ == "__main__":
    seed_data()
