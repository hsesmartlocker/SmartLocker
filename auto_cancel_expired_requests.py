import os
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv
from utils.email_sender import send_notification_email

load_dotenv()

BASE_URL = "https://hsesmartlocker.ru"
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")


def login_admin():
    res = requests.post(
        f"{BASE_URL}/auth/token",
        data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if res.status_code == 200:
        return res.json().get("access_token")
    print("[ERROR] Авторизация не удалась:", res.text)
    return None


def get_all_requests(token):
    res = requests.get(
        f"{BASE_URL}/requests/all",
        headers={"Authorization": f"Bearer {token}"}
    )
    return res.json() if res.status_code == 200 else []


def get_user_email(user_id, token):
    res = requests.get(
        f"{BASE_URL}/users/{user_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    return res.json().get("email") if res.status_code == 200 else None


def get_item_name(item_id, token):
    res = requests.get(
        f"{BASE_URL}/items/{item_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    return res.json().get("name", "Оборудование") if res.status_code == 200 else "Оборудование"


def cancel_request(request_id, token):
    res = requests.post(
        f"{BASE_URL}/requests/update-status",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "request_id": request_id,
            "status": 2,
            "reason": "Не был получен в течение 48 часов",
        }
    )
    return res.status_code == 200


def main():
    token = login_admin()
    if not token:
        return

    now = datetime.utcnow()

    for req in get_all_requests(token):
        if req.get("status") != 1:
            continue

        created_at = req.get("created")
        if not created_at:
            continue

        try:
            created_dt = datetime.fromisoformat(created_at)
        except Exception as e:
            print(f"[ERROR] Невозможно разобрать дату: {created_at} — {e}")
            continue

        if now - created_dt > timedelta(hours=48):
            req_id = req["id"]
            user_id = req["user"]
            item_id = req["item_id"]

            if cancel_request(req_id, token):
                email = get_user_email(user_id, token)
                item_name = get_item_name(item_id, token)
                if email:
                    send_notification_email(
                        email,
                        subject="Ваша заявка отменена",
                        body=(
                            f"Здравствуйте!\n\n"
                            f"Ваша заявка на оборудование «{item_name}» была автоматически отменена, "
                            f"так как вы не забрали его в течение 48 часов.\n\n"
                            f"Вы можете оформить новую заявку в приложении SmartLocker.\n\n"
                            f"С уважением,\nКоманда SmartLocker HSE"
                        )
                    )
                    print(f"[OK] Заявка {req_id} отменена и письмо отправлено")
                else:
                    print(f"[WARN] Не удалось найти email для пользователя {user_id}")


if __name__ == "__main__":
    main()