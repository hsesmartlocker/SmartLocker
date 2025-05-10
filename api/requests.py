from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from models import Request, Item, RequestStatus, User
from database import engine
from api.auth import get_current_user, get_session
from datetime import datetime, timedelta
from pydantic import BaseModel
from utils.generate_postamat_code import generate_postamat_code
from models import ArchivedRequest
from utils.email_sender import send_admin_request_email, send_notification_email
from typing import Optional

router = APIRouter(prefix="/requests", tags=["Requests"])


class RequestCreate(BaseModel):
    item_id: int
    comment: str = "Автоматическое бронирование"
    planned_return_date: datetime


class StatusUpdateData(BaseModel):
    request_id: int
    status: int
    reason: Optional[str] = None


class ChangeReturnDateRequest(BaseModel):
    request_id: int
    new_date: datetime


class StatusUpdateRequest(BaseModel):
    request_id: int
    new_status: int


@router.post("/", response_model=dict)
def create_request(data: RequestCreate, current_user: User = Depends(get_current_user)):
    with Session(engine) as session:
        item = session.get(Item, data.item_id)
        if not item or not item.available:
            raise HTTPException(status_code=400, detail="Оборудование недоступно")

        status_name = "Ожидает получения" if item.access_level == 1 else "Создана"
        status = session.exec(
            select(RequestStatus).where(RequestStatus.name == status_name)
        ).first()
        if not status:
            raise HTTPException(
                status_code=400, detail=f"Не найден статус '{status_name}'"
            )

        if item.access_level == 1:
            planned_return_date = datetime.utcnow().replace(
                hour=18, minute=0, second=0, microsecond=0
            ) + timedelta(days=3)
        else:
            if not data.planned_return_date:
                raise HTTPException(
                    status_code=400, detail="Укажите срок возврата"
                )
            planned_return_date = data.planned_return_date.replace(
                hour=18, minute=0, second=0, microsecond=0
            )

        item.status = 4
        item.available = False

        request = Request(
            status=status.id,
            user=current_user.id,
            issued_by=current_user.id,
            created=datetime.utcnow(),
            comment=data.comment,
            planned_return_date=planned_return_date,
            item_id=data.item_id,
        )

        session.add(request)
        session.add(item)
        session.commit()

        if item.access_level != 1:
            try:
                send_admin_request_email(
                    user_email=current_user.email,
                    equipment_name=item.name,
                    reason=data.comment,
                )
            except Exception as e:
                print(f"[email error] Ошибка при отправке письма: {e}")

        return {"message": "Заявка успешно создана"}


@router.get("/my")
def get_my_requests(current_user: User = Depends(get_current_user)):
    with Session(engine) as session:
        requests = session.exec(
            select(Request).where(Request.user == current_user.id).order_by(Request.created.desc())
        ).all()

        result = []
        for req in requests:
            item = session.get(Item, req.item_id)
            status = session.get(RequestStatus, req.status)
            result.append({
                "id": req.id,
                "item_name": item.name if item else "Оборудование",
                "item_specs": item.specifications if item else "Характеристики недоступны",
                "status": status.name if status else "Неизвестно",
                "planned_return_date": req.planned_return_date.isoformat() if req.planned_return_date else None,
            })
        return result


@router.get("/all")
def get_all_requests(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    if current_user.user_type != 3:
        raise HTTPException(status_code=403, detail="Только для админа")

    statement = (
        select(Request)
        .join(Item, Request.item_id == Item.id)
    )
    requests = session.exec(statement).all()

    return requests


@router.post("/update-status")
def update_request_status(
        data: StatusUpdateData,
        session: Session = Depends(get_session),
        current_user: User = Depends(get_current_user)
):
    if current_user.user_type != 3:
        raise HTTPException(status_code=403, detail="Доступ запрещён")

    request = session.exec(select(Request).where(Request.id == data.request_id)).first()
    if not request:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    user = session.exec(select(User).where(User.id == request.user)).first()
    item = session.get(Item, request.item_id)

    if data.status == 2:
        archived = ArchivedRequest(
            user=request.user,
            item_id=request.item_id,
            created=request.created,
            planned_return_date=request.planned_return_date,
            actual_return_date=None,
            comment=request.comment,
            status=2
        )
        session.add(archived)
        session.delete(request)
        session.commit()

        if user and user.email:
            try:
                body = (
                    f"Здравствуйте!\n\n"
                    f"Ваша заявка на бронирование оборудования была отклонена."
                )
                if data.reason:
                    body += f"\nПричина: {data.reason}"
                body += (
                    "\n\nЕсли у вас возникли вопросы, просто ответьте на это письмо.\n\n"
                    "С уважением,\nКоманда SmartLocker HSE"
                )
                send_notification_email(
                    to_email=user.email,
                    subject="Заявка отклонена",
                    body=body
                )
            except Exception as e:
                print(f"[Ошибка при отправке письма] {e}")

        return {"message": "Заявка отклонена и перенесена в архив"}

    request.status = data.status

    if data.status == 3 and item:
        item.status = 4
        item.available = False
        session.add(item)

    session.add(request)
    session.commit()

    if user and user.email and data.status == 3:
        try:
            send_notification_email(
                to_email=user.email,
                subject="Заявка одобрена — оборудование готово к получению",
                body=(
                    f"Здравствуйте!\n\n"
                    f"Ваша заявка на бронирование оборудования была одобрена.\n"
                    f"Вы можете забрать оборудование в течение ближайших 24 часов.\n\n"
                    f"Для получения используйте код из приложения и не забудьте ваш пропуск.\n\n"
                    f"Если возникнут вопросы, напишите нам ответом на это письмо.\n\n"
                    f"— Команда SmartLocker HSE"
                )
            )
        except Exception as e:
            print(f"[Ошибка при отправке письма] {e}")

    return {"message": "Статус заявки обновлён"}


@router.post("/requests/auto_update_status")
def auto_update_status(data: StatusUpdateRequest, db: Session = Depends(get_session)):
    request_id = data.request_id
    new_status = data.new_status

    request = db.query(Request).filter(Request.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    request.status = new_status
    db.commit()
    return {"message": "Статус обновлён автоматически"}


@router.post("/{request_id}/generate-code")
def generate_code(request_id: int, current_user: User = Depends(get_current_user)):
    with Session(engine) as session:
        request = session.get(Request, request_id)
        if not request:
            raise HTTPException(status_code=404, detail="Request not found")
        if request.user != current_user.id:
            raise HTTPException(status_code=403, detail="Forbidden")

        code, expiry = generate_postamat_code()
        request.postamat_code = code
        request.code_expiry = expiry
        session.add(request)
        session.commit()
        return {"code": code, "expires_at": expiry}


@router.post("/{request_id}/cancel", response_model=dict)
def cancel_request(request_id: int, current_user: User = Depends(get_current_user)):
    with Session(engine) as session:
        request = session.get(Request, request_id)
        if not request or request.user != current_user.id:
            raise HTTPException(status_code=403, detail="Недоступно")

        item = session.get(Item, request.item_id)
        if item:
            item.available = True
            item.status = 1
            session.add(item)

        status = session.exec(
            select(RequestStatus).where(RequestStatus.name == 'Отменена')
        ).first()

        if not status:
            raise HTTPException(status_code=400, detail="Не найден статус 'Отменена'")

        request.status = status.id
        session.commit()

        archived = ArchivedRequest.from_orm(request)
        session.add(archived)

        session.delete(request)
        session.commit()

        return {"message": "Заявка отменена и перенесена в архив"}


@router.get("/history")
def get_archived_requests(current_user: User = Depends(get_current_user)):
    with Session(engine) as session:
        requests = session.exec(
            select(ArchivedRequest)
            .where(ArchivedRequest.user == current_user.id)
            .order_by(ArchivedRequest.created.desc())
        ).all()

        result = []
        for req in requests:
            item = session.get(Item, req.item_id)
            status = session.get(RequestStatus, req.status)
            result.append({
                "id": req.id,
                "item_name": item.name if item else "Оборудование",
                "status": status.name if status else "Неизвестно",
                "created": req.created.strftime('%Y-%m-%d %H:%M'),
                "planned_return_date": req.planned_return_date.strftime(
                    '%Y-%m-%d') if req.planned_return_date else None,
            })
        return result


@router.post("/change_return_date")
def change_return_date(
        data: ChangeReturnDateRequest,
        session: Session = Depends(get_session),
        current_user: User = Depends(get_current_user)
):
    if current_user.user_type != 3:
        raise HTTPException(status_code=403, detail="Только администраторы могут изменять сроки возврата")

    request = session.exec(select(Request).where(Request.id == data.request_id)).first()
    if not request:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    user = session.exec(select(User).where(User.id == request.user)).first()
    item = session.exec(select(Item).where(Item.id == request.item_id)).first()
    if not user or not item:
        raise HTTPException(status_code=404, detail="Пользователь или оборудование не найдены")

    request.planned_return_date = data.new_date.replace(hour=18, minute=0, second=0, microsecond=0)
    session.add(request)
    session.commit()

    if user.email:
        try:
            formatted_date = request.planned_return_date.strftime("%d.%m.%Y")
            body = (
                f"Здравствуйте, {user.name or 'пользователь'}!\n\n"
                f"Срок возврата оборудования \"{item.name}\" по вашей заявке был изменён администратором.\n\n"
                f"Новая дата возврата: {formatted_date} до 21:00.\n\n"
                f"Если у вас возникнут вопросы, пожалуйста, свяжитесь с нами, ответив на это письмо.\n\n"
                f"С уважением,\nКоманда SmartLocker HSE"
            )
            send_notification_email(
                to_email=user.email,
                subject="Изменение срока возврата оборудования",
                body=body,
            )
        except Exception as e:
            print(f"[Ошибка при отправке письма] {e}")

    return {"message": "Срок возврата обновлён и письмо отправлено"}


@router.post("/req_change_return_date")
def request_return_date_change(
        data: ChangeReturnDateRequest,
        session: Session = Depends(get_session),
        current_user: User = Depends(get_current_user)
):
    request = session.exec(select(Request).where(Request.id == data.request_id)).first()
    if not request:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    item = session.exec(select(Item).where(Item.id == request.item_id)).first()
    if not item:
        raise HTTPException(status_code=404, detail="Оборудование не найдено")

    user_type = {
        1: "студент",
        2: "сотрудник",
        3: "администратор",
    }.get(current_user.user_type, "пользователь")

    new_date_str = data.new_date.strftime("%d.%m.%Y")
    created_str = request.created.strftime("%d.%m.%Y %H:%M")
    current_return_str = request.planned_return_date.strftime("%d.%m.%Y")

    subject = "Запрос на продление срока возврата"
    body = (
        f"Поступил запрос на продление:\n"
        f"Заявка №{request.id} на оборудование \"{item.name}\".\n"
        f"{user_type.title()} {current_user.name} ({current_user.email}) запрашивает продление до {new_date_str}.\n\n"
        f"Заявка создана: {created_str}\n"
        f"Текущая дата возврата: {current_return_str}\n\n"
        f"Пожалуйста, подтвердите или отклоните продление в админ-панели приложения."
    )

    try:
        send_notification_email(
            to_email="noreply-smartlocker@yandex.ru",
            subject=subject,
            body=body,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при отправке письма: {str(e)}")

    return {"message": "Запрос на продление отправлен"}
