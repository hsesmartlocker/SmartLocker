import requests
from datetime import datetime, timedelta

BASE_URL = "http://127.0.0.1:8000"

email = "student@example.com"
password = "1234"

# Авторизация
auth_response = requests.post(f"{BASE_URL}/auth/token", data={"username": email, "password": password})
token = auth_response.json().get("access_token")

if not token:
    print("Не удалось получить токен")
    print(auth_response.text)
    exit()

print("Токен получен")

headers = {"Authorization": f"Bearer {token}"}

# 1. Список пользователей
print("\n========== Список пользователей ==========")
response = requests.get(f"{BASE_URL}/users", headers=headers)
print(response.status_code)
print(response.json())

# 2. Создание заявки
print("\n========== Создание заявки ==========")
request_payload = {
    "comment": "Тестовая заявка через скрипт",
    "takendate": (datetime.utcnow() + timedelta(days=1)).isoformat(),
    "planned_return_date": (datetime.utcnow() + timedelta(days=2)).isoformat()
}
response = requests.post(f"{BASE_URL}/requests", headers=headers, json=request_payload)
print(response.status_code)
print(response.json())

# 3. Заявки текущего пользователя
print("\n========== Заявки текущего пользователя ==========")
response = requests.get(f"{BASE_URL}/requests", headers=headers)
print(response.status_code)
print(response.json())

# 4. Получение оборудования
print("\n========== Доступное оборудование ==========")
response = requests.get(f"{BASE_URL}/items/available", headers=headers)
print(response.status_code)
print(response.json())

# 5. NFC-доступ (например, терминал с id=1)
print("\n========== NFC доступ к терминалу (id=1) ==========")
response = requests.post(f"{BASE_URL}/nfc/unlock/1", headers=headers)
print(response.status_code)
print(response.json())