from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel, Column, Integer, String, ForeignKey, JSON


# Пользователи и типы
class UserType(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    active: bool = Field(default=True)
    name: Optional[str] = Field(default=None, nullable=True)
    email: str
    phone: Optional[str] = Field(default=None, nullable=True)
    created: Optional[datetime] = Field(default_factory=datetime.utcnow)
    card_id: Optional[str] = Field(default=None, nullable=True)
    user_type: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("usertype.id", ondelete='CASCADE'), nullable=True)
    )
    email_verified: Optional[bool] = Field(default=False, nullable=True)
    telegram_id: Optional[int] = Field(default=None, nullable=True)
    password: str


# Заявки
class RequestStatus(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str


class Request(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    status: int = Field(sa_column=Column(Integer, ForeignKey("requeststatus.id", ondelete='CASCADE'), nullable=False))
    user: int = Field(sa_column=Column(Integer, ForeignKey("user.id", ondelete='CASCADE'), nullable=False))
    issued_by: int = Field(sa_column=Column(Integer, ForeignKey("user.id", ondelete='CASCADE'), nullable=False))
    comment: str
    created: datetime
    takendate: datetime
    planned_return_date: datetime
    return_date: datetime


# Локации
class Terminal(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    created: datetime


class Lab(SQLModel, table=True):
    id: int = Field(primary_key=True)
    name: str
    created: datetime


class Building(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    adress: str
    created: datetime


class Room(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    lab: int = Field(sa_column=Column(Integer, ForeignKey("lab.id", ondelete='CASCADE'), nullable=False))
    created: datetime
    building: int = Field(sa_column=Column(Integer, ForeignKey("building.id", ondelete='CASCADE'), nullable=False))
    type: str


class Section(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: str
    room: int = Field(sa_column=Column(Integer, ForeignKey("room.id", ondelete='CASCADE'), nullable=False))


class TerminalAccess(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    room: int = Field(sa_column=Column(Integer, ForeignKey("room.id", ondelete='CASCADE'), nullable=False))
    terminal: int = Field(sa_column=Column(Integer, ForeignKey("terminal.id", ondelete='CASCADE'), nullable=False))


class Place(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: str
    section: int = Field(sa_column=Column(Integer, ForeignKey("section.id", ondelete='CASCADE'), nullable=False))


# Доступы
class UserAccess(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user: int = Field(sa_column=Column(Integer, ForeignKey("user.id", ondelete='CASCADE'), nullable=False))
    room: int = Field(sa_column=Column(Integer, ForeignKey("room.id", ondelete='CASCADE'), nullable=False))


# Оборудование
class HardwareType(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    hardware_specifications_template: dict = Field(sa_type=JSON)


class Hardware(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    type: int = Field(sa_column=Column(Integer, ForeignKey("hardwaretype.id", ondelete='CASCADE'), nullable=False))
    image_link: str
    specifications: dict = Field(sa_type=JSON)
    item_specifications: dict = Field(sa_type=JSON)


class ItemStatus(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str


class GroupStatus(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str


class Group(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    group_key: str
    status: int = Field(sa_column=Column(Integer, ForeignKey("groupstatus.id", ondelete='CASCADE'), nullable=False))
    created: datetime
    parent: Optional[int] = Field(default=None, sa_column=Column(Integer, ForeignKey("group.id", ondelete='CASCADE')))
    available: bool


class RequestGroup(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    group: Optional[int] = Field(default=None, sa_column=Column(Integer, ForeignKey("group.id", ondelete='CASCADE')))
    request: Optional[int] = Field(default=None, sa_column=Column(Integer, ForeignKey("request.id", ondelete='CASCADE')))


class Item(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    inv_key: str
    hardware: int = Field(sa_column=Column(Integer, ForeignKey("hardware.id", ondelete='CASCADE'), nullable=False))
    group: int
    status: int = Field(sa_column=Column(Integer, ForeignKey("itemstatus.id", ondelete='CASCADE'), nullable=False))
    owner: str
    place: int = Field(sa_column=Column(Integer, ForeignKey("place.id", ondelete='CASCADE'), nullable=False))
    available: bool
    specifications: dict = Field(sa_type=JSON)


class QualityComment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    request: int = Field(sa_column=Column(Integer, ForeignKey("request.id", ondelete='CASCADE'), nullable=False))
    grade: int
    comment: str
    item: int = Field(sa_column=Column(Integer, ForeignKey("item.id", ondelete='CASCADE'), nullable=False))
    photo_link: str


# История
class OperationType(SQLModel, table=True):
    name: str = Field(primary_key=True)


class History(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    entity: str
    entity_id: int
    data: dict = Field(sa_type=JSON)
    created: datetime
    type: str = Field(sa_column=Column(String, ForeignKey("operationtype.name", ondelete='CASCADE'), nullable=False))

class RegistrationCode(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str
    code: str
    created_at: datetime = Field(default_factory=datetime.utcnow)