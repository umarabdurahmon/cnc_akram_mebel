# Сессия 2 — Посещения: ядро (kickoff для Claude Code)

> Предусловие: Сессия 1 пройдена — есть модель `employee`, авторизация через
> `initData`, зависимость `get_current_employee`, тестовая фикстура для
> генерации валидной initData в `conftest.py`. Открой папку в Claude Code и
> вставь промпт ниже.
>
> Объём осознанно ограничен ядром данных. Сверка по камере и ручная правка
> руководителем — отдельная Сессия 2b. Vue-интерфейс — Сессия 3.

---

## Промпт

Прочитай `CLAUDE.md` и `docs/тз.md` (разделы 7.1 и 9.2). Сначала план, потом код.
Останавливайся на ревью перед миграцией и перед коммитом.

### 1. Модель `attendance_record` (тз 9.2)

`app/models/attendance.py`, SQLAlchemy 2.x (typed `Mapped`):
- `id` PK
- `employee_id` FK → employee
- `work_date` DATE
- `check_in_at` TIMESTAMPTZ
- `check_out_at` TIMESTAMPTZ, NULL (NULL = визит открыт)
- `verification_status` нативный enum `(not_checked, confirmed, discrepancy)`,
  default `not_checked`
- `verified_by` FK → employee, NULL
- `verified_at` TIMESTAMPTZ, NULL
- `note` TEXT, NULL
- `created_at`, `updated_at` TIMESTAMPTZ

Ограничения (на уровне БД, не только в коде):
- частичный уникальный индекс: `UNIQUE(employee_id) WHERE check_out_at IS NULL`;
- индекс по `(employee_id, work_date)` для отчётов.

### 2. Миграция

`make revision m="attendance table"`. ENUM `verification_status` — снова случай
капризного автогена Alembic: покажи файл на ревью, проверь `CREATE TYPE` в upgrade
и `DROP TYPE` в downgrade, а также что частичный индекс сгенерился с условием
`WHERE check_out_at IS NULL`. Не применяй до одобрения.

### 3. Часовой пояс предприятия

Добавь настройку `SHOP_TZ` (значение `Asia/Tashkent`) в конфиг и в `.env.example`.
`work_date` ВСЕГДА вычисляется приведением `check_in_at` к `SHOP_TZ`, а не из UTC.
Группировки и подсчёт часов по дням идут через эту дату.

### 4. Сервис-переключатель (главная логика)

`app/services/attendance.py`, функция `toggle(employee_id)`:
- если у сотрудника есть открытый визит (`check_out_at IS NULL`) → проставить
  `check_out_at = now()`, вернуть закрытый визит;
- иначе → создать открытый визит (`work_date` в `SHOP_TZ`).

Защита от гонки (несущая, не опускать):
- INSERT открытого визита оборачивай в `try/except IntegrityError`. При нарушении
  частичного индекса — поймать, достать существующий открытый визит и вернуть его
  (двойной тап «Пришёл» = идемпотентно, без 500).
- Двойной тап «Ушёл»: НЕ открывай новый визит, если предыдущий визит сотрудника
  был закрыт в пределах короткого окна (напр. 5 секунд). Иначе закрытие случайно
  «возвращает» человека на смену.

### 5. Подсчёт часов

`hours_for_day` / `hours_for_period`:
- сумма длительностей ЗАКРЫТЫХ визитов (`check_out_at - check_in_at`);
- открытый визит в сумму не входит, отдаётся отдельным полем «на смене с HH:MM»;
- за месяц = сумма по дням.

### 6. Эндпоинты

- `POST /api/attendance/toggle` — переключатель для текущего сотрудника
  (через `get_current_employee`); ответ: `{open: bool, visit: {...}, today_hours}`.
- `GET /api/attendance/me/today` — мои визиты и часы за сегодня.
- `GET /api/attendance/summary?date=...` (и/или период) — сводка для руководителя:
  кто отметился, времена визитов, суммарные часы. ТОЛЬКО роль manager.

### 7. Несущие тесты (только эти, против настоящего Postgres, через auth-фикстуру)

- два открытых визита для одного сотрудника → `IntegrityError` (индекс работает);
- повторный `toggle` на check-in → один визит, без 500, отдан существующий;
- check-in затем check-out → длительность считается, визит закрыт;
- двойной check-out не открывает новый визит;
- часы за день = сумма закрытых визитов; открытый не входит в сумму;
- `work_date` для прихода у которого UTC и локальная дата различаются —
  присваивается по `Asia/Tashkent`, не по UTC;
- `summary` доступен manager, рабочему — 403.

### Definition of Done (Сессия 2)

- `make migrate` создаёт таблицу, enum и частичный индекс; downgrade чист.
- Рабочий через `/api/attendance/toggle` отмечает приход и уход; двойной тап
  безопасен. Руководитель видит сводку за день.
- `make check` зелёный, показан вывод.
- Закоммичено мелкими логическими коммитами.

Сверка по камере (`confirmed`/`discrepancy`) и ручное редактирование записей
руководителем — НЕ в этой сессии (Сессия 2b).
