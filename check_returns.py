import os
import sys
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

load_dotenv()

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
BASE_URL = "https://hsesmartlocker.ru"

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.email_sender import send_notification_email


def login_as_admin():
    res = requests.post(
        f"{BASE_URL}/auth/token",
        data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if res.status_code == 200:
        return res.json().get("access_token")
    else:
        print("Не удалось авторизоваться как админ:", res.text)
        return None


def fetch_all_requests(token):
    res = requests.get(
        f"{BASE_URL}/requests/all",
        headers={"Authorization": f"Bearer {token}"}
    )
    return res.json() if res.status_code == 200 else []


def fetch_user_email(user_id, token):
    res = requests.get(
        f"{BASE_URL}/users/{user_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    return res.json().get("email") if res.status_code == 200 else None


def fetch_item_name(item_id, token):
    res = requests.get(
        f"{BASE_URL}/items/{item_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    return res.json().get("name", "Оборудование") if res.status_code == 200 else "Оборудование"


def update_request_status(request_id, new_status, token):
    res = requests.post(
        f"{BASE_URL}/requests/auto_update_status",
        json={"request_id": request_id, "new_status": new_status},
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
    )
    return res.status_code == 200


def main():
    token = login_as_admin()
    if not token:
        return

    now = datetime.utcnow() + timedelta(hours=3)  # МСК

    for req in fetch_all_requests(token):
        return_raw = req.get("planned_return_date")
        if not return_raw:
            continue

        print(return_raw)

        try:
            return_dt = datetime.fromisoformat(return_raw)
        except Exception as e:
            print("Ошибка в дате:", e)
            continue

        diff = return_dt - now
        user_id = req["user"]
        request_id = req["id"]
        item_name = fetch_item_name(req["item_id"], token)
        user_email = fetch_user_email(user_id, token)

        if not user_email:
            continue

        if 0 < diff.total_seconds() <= 86400 and req["status"] != 5:
            if update_request_status(request_id, 5, token):
                deadline = return_dt.replace(tzinfo=None).strftime("%H:%M %d.%m.%Y")
                send_notification_email(
                    user_email,
                    "Напоминание о скором возврате оборудования",
                    f"Уважаемый пользователь,\n\nВы арендовали оборудование: «{item_name}».\nПожалуйста, верните его до {deadline}.\n\nЕсли у вас возникли затруднения, напишите в поддержку.\n\nС уважением,\nКоманда SmartLocker"
                )

        elif diff.total_seconds() <= 0 and req["status"] != 7:
            if update_request_status(request_id, 7, token):
                send_notification_email(
                    user_email,
                    "Срок возврата оборудования истёк",
                    f"Уважаемый пользователь,\n\nВы не вернули оборудование: «{item_name}» в установленный срок.\nПожалуйста, срочно верните его в постамат.\n\nЕсли возникли сложности — напишите в ответном письме или обратитесь в поддержку.\n\nС уважением,\nКоманда SmartLocker"
                )


if __name__ == "__main__":
    main()
