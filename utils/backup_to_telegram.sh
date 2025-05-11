#!/bin/bash

# === ПАРАМЕТРЫ БД ===
DB_NAME="smartlocker"
DB_USER="postgres"
DB_PASS="smartpass"

# === TELEGRAM ===
BOT_TOKEN="7651421567:AAH1jsLy2SpSv5MCLnw7J_HMsAX5jbhQGeY"
CHAT_ID="562306231"

# === ИМЯ ФАЙЛА БЕЗ ПРОБЕЛОВ И ДВОЕТОЧИЙ ===
NOW=$(date +"%Y%m%d_%H%M")
FILE="/tmp/smartlocker_backup_${NOW}.sql"

# === СОЗДАНИЕ ДАМПА ===
PGPASSWORD="$DB_PASS" pg_dump -U "$DB_USER" -h localhost "$DB_NAME" > "$FILE"

# === ПРОВЕРКА, ЧТО ФАЙЛ СОЗДАН ===
if [ ! -f "$FILE" ]; then
  echo "Ошибка: файл дампа не создан!"
  exit 1
fi

# === ОТПРАВКА В TELEGRAM ===
curl -s -X POST "https://api.telegram.org/bot$BOT_TOKEN/sendDocument" \
  -F chat_id="$CHAT_ID" \
  -F document=@"$FILE" \
  -F caption="SmartLocker Backup $NOW"

# === УДАЛЕНИЕ ФАЙЛА ===
rm "$FILE"