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
    item_id: int = Field(foreign_key="item.id")
    user: int = Field(sa_column=Column(Integer, ForeignKey("user.id", ondelete='CASCADE'), nullable=False))
    issued_by: int = Field(sa_column=Column(Integer, ForeignKey("user.id", ondelete='CASCADE'), nullable=False))
    comment: str
    created: datetime
    takendate: datetime
    planned_return_date: datetime
    return_date: datetime


# Оборудование
class ItemStatus(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str


class Item(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    inv_key: str
    name: str
    status: int = Field(sa_column=Column(Integer, ForeignKey("itemstatus.id", ondelete='CASCADE'), nullable=False))
    owner: str
    place: int = Field(sa_column=Column(Integer, ForeignKey("place.id", ondelete='CASCADE'), nullable=False))
    available: bool
    specifications: dict = Field(sa_type=JSON)
    access_level: int = Field(default=1)

    class Config:
        orm_mode = True


class RegistrationCode(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str
    code: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
