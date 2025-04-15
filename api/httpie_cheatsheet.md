
# HTTPie-шпаргалка для SmartLocker API

## Получить токен авторизации

```bash
http -f POST http://127.0.0.1:8000/auth/token \
    username=student@example.com \
    password=1234
```

Сохрани токен в переменную:
```bash
TOKEN=eyJhbGciOi...  # вставь полученный токен
```

---

## Получить список пользователей

```bash
http GET http://127.0.0.1:8000/users/ \
    "Authorization: Bearer $TOKEN"
```

---

## Создать заявку

```bash
http POST http://127.0.0.1:8000/requests/ \
    takendate="2025-04-10T14:00:00" \
    planned_return_date="2025-04-12T18:00:00" \
    comment="Нужен ноутбук" \
    "Authorization: Bearer $TOKEN"
```

---

## Получить все свои заявки

```bash
http GET http://127.0.0.1:8000/requests/ \
    "Authorization: Bearer $TOKEN"
```

---

## Получить доступные предметы

```bash
http GET http://127.0.0.1:8000/items/available \
    "Authorization: Bearer $TOKEN"
```

---

## Вернуть оборудование по заявке

```bash
http POST http://127.0.0.1:8000/return/1 \
    "Authorization: Bearer $TOKEN"
```

---

## Разблокировать терминал (по NFC)

```bash
http POST http://127.0.0.1:8000/nfc/unlock/1 \
    "Authorization: Bearer $TOKEN"
```

