import smtplib
from email.mime.text import MIMEText

EMAIL_FROM = "noreply-smartlocker@ya.ru"
EMAIL_PASSWORD = "kizdoz-nyrbaX-8bopgu"

def send_confirmation_email(to_email: str, code: str):
    msg = MIMEText(f"Ваш код подтверждения: {code}")
    msg["Subject"] = "Код подтверждения SmartLocker"
    msg["From"] = EMAIL_FROM
    msg["To"] = to_email

    with smtplib.SMTP_SSL("smtp.yandex.ru", 465) as server:
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.send_message(msg)