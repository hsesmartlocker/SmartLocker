from sqlmodel import Session
from datetime import datetime

from database import engine
from models import (
    UserType, RequestStatus, GroupStatus, ItemStatus, OperationType,
    Building, Lab, Room, Section, Terminal, TerminalAccess,
    User, UserAccess, HardwareType, Hardware, Group,
    Place, Item, Request
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
        session.add_all([status_waiting, status_issued, status_returned])
        session.commit()

        group_status_active = GroupStatus(name="Активна")
        group_status_deleted = GroupStatus(name="Удалена")
        session.add_all([group_status_active, group_status_deleted])
        session.commit()

        item_free = ItemStatus(name="Свободен")
        item_issued = ItemStatus(name="Выдан")
        item_broken = ItemStatus(name="Сломан")
        session.add_all([item_free, item_issued, item_broken])
        session.commit()

        session.add_all([
            OperationType(name="create"),
            OperationType(name="update"),
            OperationType(name="delete"),
        ])
        session.commit()

        # === Локации ===
        building = Building(name="Главный корпус", adress="Улица Академика, д.1", created=datetime.utcnow())
        lab = Lab(name="Лаборатория тестов", created=datetime.utcnow())
        session.add_all([building, lab])
        session.commit()

        room = Room(name="Аудитория 101", lab=lab.id, building=building.id, type="учебная", created=datetime.utcnow())
        session.add(room)
        session.commit()

        section = Section(name="Секция 1", description="Секция с ноутбуками", room=room.id)
        session.add(section)
        session.commit()

        terminal = Terminal(name="Терминал 1", created=datetime.utcnow())
        session.add(terminal)
        session.commit()

        session.add(TerminalAccess(room=room.id, terminal=terminal.id))
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

        session.add(UserAccess(user=user.id, room=room.id))
        session.commit()

        # === Оборудование ===
        hw_type = HardwareType(name="Ноутбук", hardware_specifications_template={"CPU": "string", "RAM": "string"})
        session.add(hw_type)
        session.commit()

        hardware = Hardware(
            name="Dell Latitude",
            type=hw_type.id,
            image_link="https://example.com/image.jpg",
            specifications={"CPU": "Intel i5", "RAM": "16GB"},
            item_specifications={"SSD": "512GB"}
        )
        session.add(hardware)
        session.commit()

        group = Group(group_key="GRP001", status=group_status_active.id, created=datetime.utcnow(), parent=None, available=True)
        session.add(group)
        session.commit()

        place = Place(name="Место хранения 1", description="Ячейка в секции 1", section=section.id)
        session.add(place)
        session.commit()

        item = Item(
            inv_key="INV001",
            hardware=hardware.id,
            group=group.id,
            status=item_free.id,
            owner="МИЭМ",
            place=place.id,
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