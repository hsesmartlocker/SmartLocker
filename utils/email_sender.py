import smtplib
from email.mime.text import MIMEText

EMAIL_FROM = "noreply-smartlocker@yandex.ru"
EMAIL_PASSWORD = "rxfjyyycrgesjcus"


def send_confirmation_email(to_email: str, code: str):
    msg = MIMEText(f"Ваш код подтверждения: {code}")
    msg["Subject"] = "Код подтверждения SmartLocker"
    msg["From"] = EMAIL_FROM
    msg["To"] = to_email

    with smtplib.SMTP_SSL("smtp.yandex.ru", 465) as server:
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.send_message(msg)


def send_admin_request_email(user_email: str, equipment_name: str, reason: str):
    from datetime import datetime, timedelta

    deadline = (datetime.now() + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M")
    body = f"""
Новая заявка от {user_email}
на оборудование: {equipment_name}

Причина:
{reason}

Пожалуйста, рассмотрите её до {deadline}.
"""

    msg = MIMEText(body)
    msg["Subject"] = f"Заявка на {equipment_name} от {user_email}"
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_FROM

    with smtplib.SMTP_SSL("smtp.yandex.ru", 465) as server:
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.send_message(msg)


def send_support_message(user_email: str, message: str):
    body = f"""
Обращение от пользователя: {user_email}

Текст обращения:
{message}
"""
    msg = MIMEText(body)
    msg["Subject"] = f"Обращение в поддержку от {user_email}"
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_FROM

    with smtplib.SMTP_SSL("smtp.yandex.ru", 465) as server:
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.send_message(msg)


def send_temporary_password_email(to_email: str, new_password: str):
    body = f"""
    Ваш новый пароль от SmartLocker:

    {new_password}

    Не забудьте сменить его в личном кабинете после входа.
    """
    msg = MIMEText(body)
    msg["Subject"] = "Новый пароль SmartLocker"
    msg["From"] = EMAIL_FROM
    msg["To"] = to_email

    with smtplib.SMTP_SSL("smtp.yandex.ru", 465) as server:
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.send_message(msg)


def send_notification_email(to_email: str, subject: str, body: str):
    """
    Универсальная функция для отправки уведомлений пользователю.
    """
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = to_email

    with smtplib.SMTP_SSL("smtp.yandex.ru", 465) as server:
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.send_message(msg)
