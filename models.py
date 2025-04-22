from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel, Column, Integer, String, ForeignKey, JSON
from sqlalchemy import CheckConstraint


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
    takendate: Optional[datetime] = Field(default=None, nullable=True)
    planned_return_date: datetime
    return_date: Optional[datetime] = Field(default=None, nullable=True)
    item_id: int = Field(sa_column=Column(Integer, ForeignKey("item.id", ondelete='CASCADE'), nullable=False))
    postamat_code: Optional[str] = None
    code_expiry: Optional[datetime] = None


# Оборудование
class ItemStatus(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str


# Таблица с расположением ячеек
class CellLocation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str  # Пример: "слева", "справа-снизу", "по центру"

# Таблица ячеек хранения
class Cell(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    size: str  # Значения: 'S', 'M', 'L'
    location_id: int = Field(sa_column=Column(Integer, ForeignKey("celllocation.id", ondelete="CASCADE")))
    is_free: bool = Field(default=True)

# Обновляем модель Item
class Item(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    inv_key: str
    name: str
    status: int = Field(sa_column=Column(Integer, ForeignKey("itemstatus.id", ondelete='CASCADE'), nullable=False))
    owner: str
    available: bool
    access_level: int
    specifications: dict = Field(sa_type=JSON)
    # Новое поле: в какой ячейке лежит предмет
    cell: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("cell.id", ondelete="SET NULL"))
    )

    __table_args__ = (
        CheckConstraint('cell BETWEEN 1 AND 20', name='cell_range_check'),
    )


class RegistrationCode(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str
    code: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
