
# SmartLocker API

**SmartLocker API** — это серверное приложение на FastAPI для автоматизации бронирования, выдачи и возврата оборудования через мобильное приложение и NFC-терминалы.

---

## Запуск

```bash
uvicorn main:app --reload
```

---

## Авторизация

Используется OAuth2 с JWT.

### Получить токен:
```http
POST /auth/token
Content-Type: application/x-www-form-urlencoded

username=student@example.com
password=1234
```

Ответ:
```json
{
  "access_token": "jwt-token",
  "token_type": "bearer"
}
```

Используй заголовок в дальнейшем:
```
Authorization: Bearer <токен>
```

---

## Пользователи

### `GET /users/`
Список всех пользователей (требуется токен)

### `GET /users/{user_id}`
Информация о конкретном пользователе

---

## Заявки

### `POST /requests/`

Создать заявку:
```json
{
  "takendate": "2025-04-10T14:00:00",
  "planned_return_date": "2025-04-12T18:00:00",
  "comment": "Нужен ноутбук"
}
```

### `GET /requests/`
Список заявок текущего пользователя

---

## Оборудование

### `GET /items/`
Список всех предметов

### `GET /items/available`
Список свободных предметов

### `GET /items/hardware/{id}`
Все предметы данной модели

---

## Возврат

### `POST /return/{request_id}`
Возврат оборудования по заявке

---

## NFC доступ

### `POST /nfc/unlock/{terminal_id}`
Проверка, может ли пользователь открыть данный терминал

---

## Инициализация справочников

```bash
python init_data.py
```

Добавляет:
- Типы пользователей
- Статусы заявок, предметов, групп
- Типы операций

---

## Требуемые библиотеки

```txt
fastapi
uvicorn
sqlmodel
psycopg2-binary
python-jose
pydantic
```

---

## Автор
Всеволод Кудинов, БИВ211, МИЭМ НИУ ВШЭ
