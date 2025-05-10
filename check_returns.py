import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://hsesmartlocker.ru"
EMAIL_ADMIN = os.getenv("ADMIN_EMAIL")
PASSWORD_ADMIN = os.getenv("ADMIN_PASSWORD")
HEADERS = {}


def login_as_admin():
    global HEADERS
    res = requests.post(
        f"{API_URL}/auth/token",
        data={"username": EMAIL_ADMIN, "password": PASSWORD_ADMIN},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if res.status_code != 200:
        raise Exception("Не удалось авторизоваться как админ")
    token = res.json()["access_token"]
    HEADERS = {"Authorization": f"Bearer {token}"}


def fetch_requests():
    res = requests.get(f"{API_URL}/requests/all", headers=HEADERS)
    if res.status_code != 200:
        raise Exception("Не удалось получить список заявок")
    return res.json()


def notify_user(email, subject, message):
    requests.post(
        f"{API_URL}/email/send",
        headers=HEADERS,
        json={"email": email, "subject": subject, "message": message},
    )


def update_status(req_id, new_status):
    requests.post(
        f"{API_URL}/requests/update_status",
        headers=HEADERS,
        json={"request_id": req_id, "status": new_status},
    )


def main():
    login_as_admin()
    all_requests = fetch_requests()
    now = datetime.utcnow() + timedelta(hours=3)  # по МСК

    for req in all_requests:
        status = req["status"]
        return_raw = req.get("planned_return_date")
        if not return_raw:
            continue

        return_time = datetime.fromisoformat(return_raw)
        hours_left = (return_time - now).total_seconds() / 3600

        if status in [1, 3] and 0 < hours_left < 24:
            update_status(req["id"], 5)
            notify_user(
                req["user_email"],
                "Напоминание о возврате оборудования",
                f"Уважаемый пользователь! Напоминаем, что срок возврата оборудования ({req['item_name']}) истекает завтра в 21:00. Пожалуйста, верните его своевременно в постамат."
            )
        elif status in [1, 3] and hours_left <= 0:
            update_status(req["id"], 7)
            notify_user(
                req["user_email"],
                "Просрочен возврат оборудования",
                f"Уважаемый пользователь! Срок возврата оборудования ({req['item_name']}) уже истёк. Срочно верните оборудование в постамат. Если у вас возникли затруднения — ответьте на это письмо или обратитесь в поддержку."
            )


if __name__ == "__main__":
    main()
