# Сессия 1 — Авторизация + employee (kickoff для Claude Code)

> Предусловие: Сессия 0 пройдена — каркас стоит, `make check` зелёный,
> health-эндпоинт жив, бот отвечает на `/start`. Открой папку в Claude Code и
> вставь промпт ниже.

---

## Промпт

Прочитай `CLAUDE.md` и `docs/тз.md` (особенно разделы 5, 6.1, 7.6, 9.1).

Задача этой сессии — авторизация сотрудников через Telegram `initData` и модель
`employee` с первой содержательной миграцией. Сначала покажи план, потом код.
Останавливайся на ревью перед миграцией и перед коммитом.

### 1. Модель `employee` (тз 9.1)

`app/models/employee.py`, SQLAlchemy 2.x (typed `Mapped`):
- `id` PK
- `telegram_id` BIGINT, UNIQUE, NOT NULL
- `full_name` TEXT
- `role` нативный enum Postgres `(worker, manager)`
- `language` нативный enum Postgres `(ru, uz)`
- `position` TEXT, nullable
- `is_active` BOOLEAN, default true
- `created_at` TIMESTAMPTZ, default now()

### 2. Первая содержательная миграция

`alembic revision --autogenerate -m "employee table"`.
ВАЖНО: автоген Alembic ненадёжно создаёт нативные ENUM-типы Postgres. После
генерации покажи мне файл миграции на ревью. Проверь руками, что в `upgrade`
enum-типы создаются (`sa.Enum(..., name=...)`), а в `downgrade` — удаляются
(`DROP TYPE`). Не применяй миграцию до моего одобрения.

### 3. Проверка initData — через aiogram, НЕ руками

В `app/core/security.py` используй встроенный помощник:
```python
from aiogram.utils.web_app import safe_parse_webapp_init_data
# бросает ValueError при невалидной/подделанной подписи
data = safe_parse_webapp_init_data(token=settings.bot_token, init_data=raw)
```
Не реализуй HMAC вручную. Дополнительно сам проверь свежесть `auth_date`
(отклоняй initData старше разумного окна, напр. 24ч) для защиты от повтора.

### 4. Контракт передачи и зависимость аутентификации

- Фронт передаёт сырую строку initData в заголовке `Authorization: tma <initData>`.
- FastAPI-зависимость `get_current_employee`:
  1. достаёт строку из заголовка (нет → 401);
  2. валидирует через `safe_parse_webapp_init_data` (ValueError → 401);
  3. берёт `telegram_id` ТОЛЬКО из разобранного результата, не из тела запроса;
  4. ищет сотрудника по `telegram_id` (нет → 403);
  5. проверяет `is_active` (false → 403);
  6. возвращает объект `employee`.
- НИКОГДА не доверяй `initDataUnsafe` с фронта — только валидированная строка.

### 5. Эндпоинт `/api/me`

`GET /api/me` через зависимость `get_current_employee` возвращает безопасный
профиль (id, full_name, role, language, position). Это проверка, что вся цепочка
авторизации работает end-to-end.

### 6. Seed первого руководителя (решает проблему «пустой таблицы»)

Войти нельзя, пока сотрудника нет в базе, а сам себя `/start` не заводит.
Сделай management-скрипт + цель Makefile:
`make seed-manager TG_ID=<telegram_id> NAME="<ФИО>"` — создаёт (или обновляет до)
руководителя с указанным `telegram_id`. Идемпотентно.

### 7. Несущие тесты (только эти, против настоящего Postgres)

- валидная initData → `/api/me` отдаёт 200 и правильного сотрудника;
- подделанная/битая initData → 401;
- отсутствие заголовка → 401;
- валидная подпись, но `telegram_id` нет в базе → 403;
- сотрудник с `is_active=false` → 403.
Для генерации валидной тестовой initData подпиши строку тем же алгоритмом, что и
Telegram, тестовым токеном (можно через `check_webapp_signature` aiogram как
обратную сверку). Каждый тест — в транзакции с откатом.

### Definition of Done (Сессия 1)

- `make migrate` создаёт таблицу `employee` и enum-типы; `downgrade` чисто
  откатывает (проверено).
- `make seed-manager TG_ID=... NAME=...` заводит руководителя.
- `/api/me` с реальной initData из Telegram возвращает профиль засиженного
  руководителя; с мусором — 401.
- `make check` зелёный, показан его вывод.
- Закоммичено мелкими логическими коммитами.

Язык сотрудника (`language`) при создании бери из Telegram `language_code`
(ru/uz), с дефолтом. Переключение языка вручную — НЕ в этой сессии.
