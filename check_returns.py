from datetime import datetime, timedelta
from sqlmodel import Session, select
from database import engine
from models import Request, Item, User
from utils.email_sender import send_notification_email


def check_deadlines():
    now_msk = datetime.utcnow() + timedelta(hours=3)

    with Session(engine) as session:
        requests = session.exec(select(Request).where(Request.status.in_([1, 3]))).all()

        for req in requests:
            if not req.planned_return_date:
                continue

            planned_msk = req.planned_return_date + timedelta(hours=3)
            time_left = planned_msk - now_msk

            user = session.get(User, req.user_id)
            item = session.get(Item, req.item_id)

            if not user or not item:
                continue

            item_name = item.name or "оборудование"

            # Менее 24 часов до возврата
            if timedelta(hours=0) < time_left <= timedelta(hours=24) and req.status != 5:
                req.status = 5
                session.add(req)
                send_notification_email(
                    to=user.email,
                    subject="Напоминание о возврате оборудования",
                    body=(
                        f"Уважаемый(ая) {user.name},\n\n"
                        f"Напоминаем, что срок возврата оборудования — «{item_name}» — "
                        f"истекает {planned_msk.strftime('%d.%m.%Y в %H:%M')} (по МСК).\n"
                        "Пожалуйста, верните его до этого времени в постамат SmartLocker.\n\n"
                        "С уважением,\nКоманда SmartLocker HSE"
                    )
                )

            # Срок возврата уже прошёл
            elif now_msk > planned_msk and req.status != 7:
                req.status = 7
                session.add(req)
                send_notification_email(
                    to=user.email,
                    subject="Срок возврата оборудования истёк",
                    body=(
                        f"Уважаемый(ая) {user.name},\n\n"
                        f"Срок возврата оборудования — «{item_name}» — истёк {planned_msk.strftime('%d.%m.%Y в %H:%M')} (по МСК).\n"
                        "Просим срочно вернуть оборудование в постамат.\n"
                        "Если у вас возникли сложности — ответьте на это письмо, и мы вам поможем.\n\n"
                        "С уважением,\nКоманда SmartLocker HSE"
                    )
                )

        session.commit()
        print("Проверка сроков завершена")


if __name__ == "__main__":
    check_deadlines()
