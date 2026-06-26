# Навигация по проекту

Быстрый путеводитель: где что живёт. Источник истины по требованиям — `docs/тз.md`.

---

## Корень проекта

| Путь | Что это |
|---|---|
| `Makefile` | Все команды разработки (`make check`, `make dev-api`, …) |
| `docker-compose.yml` | Postgres-контейнер (порт 5432) |
| `.env` / `.env.example` | Переменные окружения (`DATABASE_URL`, `BOT_TOKEN`, …) |
| `docs/тз.md` | Полное техническое задание — источник истины |
| `docs/color-system.md` | CSS-токены фронтенда, правила их применения |
| `docs/nav.md` | Этот файл |
| `server/` | Python-бэкенд (FastAPI + бот) |
| `frontend/` | Vue 3 Mini App |
| `scripts/gen_dev_init_data.py` | Генератор тестовой initData (dev-only) |

---

## Бэкенд (`server/`)

### Точки входа

| Файл | Что это |
|---|---|
| `server/app/main.py` | FastAPI-приложение; монтирует все роутеры |
| `server/bot/main.py` | Бот сотрудников (aiogram): `/start`, поиск по коду, midnight rollover |
| `server/bot/client_bot.py` | Клиентский бот: поиск заказа по `public_code`, сохранение `customer_chat_id` |

### Конфиг и инфраструктура

| Файл | Что это |
|---|---|
| `server/app/core/config.py` | `Settings` (pydantic-settings): `database_url`, `bot_token`, `client_bot_token`, `miniapp_url`, `storage_root`, `shop_tz` |
| `server/app/core/security.py` | `verify_init_data()` — HMAC-проверка Telegram initData (24 ч. TTL) |
| `server/app/db/session.py` | SQLAlchemy engine + `get_db()` (FastAPI dependency) |
| `server/app/api/deps.py` | `get_current_employee()` — читает `Authorization: tma <initData>`, возвращает `Employee` |
| `server/app/repositories/employee.py` | `get_by_telegram_id()` — единственный репозиторий |
| `server/bot/throttle.py` | `RateLimiter` (5 запросов / 60 сек) для клиентского бота |
| `server/bot/i18n/` | Строки бота на `ru` / `uz` |

### ORM-модели (`server/app/models/`)

| Файл | Модели |
|---|---|
| `base.py` | `Base` (DeclarativeBase) |
| `employee.py` | `Employee`, `EmployeeRole` (worker/manager), `EmployeeLanguage` (ru/uz) |
| `attendance.py` | `AttendanceRecord`, `VerificationStatus` (not_checked/confirmed/discrepancy) |
| `order.py` | `ProductionStage`, `Order`, `OrderEmployee`, `OrderFile`, `OrderStatusHistory`, `FileKind` |
| `finance.py` | `ExpenseCategory`, `OrderPayment`, `OrderExpense`, `ExpenseDirection`, `OperatingExpense` |
| `company.py` | `CompanySettings` (singleton, id=1; показывается клиентам в футере) |

### API-роутеры (`server/app/api/`) — все монтируются с префиксом `/api`

| Файл | Маршруты |
|---|---|
| `health.py` | `GET /health` |
| `me.py` | `GET /me` — текущий сотрудник |
| `attendance.py` | `POST /attendance/toggle`, `GET /attendance/*`, `PATCH`, `POST /verify` |
| `stages.py` | CRUD справочника этапов производства |
| `orders.py` | CRUD заказов, смена этапа, история, прикрепление сотрудников |
| `files.py` | `POST /orders/{id}/files`, `GET` файлов, миниатюры |
| `employees.py` | `GET /employees` (список для менеджера) |
| `categories.py` | CRUD категорий расходов |
| `finance.py` | Платежи, расходы по заказу, ежемесячный отчёт, отчёт по заказам |
| `operating_expenses.py` | Операционные расходы предприятия |
| `company.py` | `GET/PATCH /company/settings` |

### Сервисы (`server/app/services/`) — основная бизнес-логика, используется и API и ботом

| Файл | Что делает |
|---|---|
| `attendance.py` | `toggle()`, `hours_for_day/period()`, `verify_record()`, `patch_record()`, `rollover_midnight_visits()`, `get_discrepancies()` |
| `order.py` | `create_order()`, `update_order()`, `close_order()`, `change_stage()`, `get_history()`, `list_orders()` |
| `order_employee.py` | Прикрепление / открепление рабочих к заказу, `can_change_status` |
| `order_file.py` | Загрузка файлов, генерация миниатюр (Pillow) |
| `finance.py` | `add_payment()`, `add_expense()`, `monthly_report()`, `orders_detail_report()`, `employee_wages_report()` |
| `catalog.py` | CRUD `ProductionStage` (мягкое удаление через `is_active`) |
| `expense_category.py` | CRUD `ExpenseCategory` (мягкое удаление) |
| `client_view.py` | `serialize_for_client()` — WHITELIST сериализатор, **никогда** не отдаёт деньги/файлы/сотрудников/комментарии; `find_order_by_code()` |
| `company_settings.py` | `get_or_create()`, `update_settings()`, `format_footer()` |
| `telegram_notify.py` | Отправка уведомлений клиенту через клиентский бот |
| `file_type.py` | Определение `FileKind` по MIME-типу |

### Хранилище файлов (`server/app/storage/`)

| Файл | Что это |
|---|---|
| `base.py` | `Storage` Protocol: `save()`, `open()`, `delete()` |
| `local.py` | Реализация на локальной ФС (путь = `storage_root/{key}`) |
| `deps.py` | FastAPI-dependency `get_storage()` |

Файлы физически лежат в `server/storage/orders/{order_id}/{uuid}.{ext}`.

### Схемы (Pydantic) — `server/app/schemas/`

По одному файлу на домен: `attendance.py`, `catalog.py`, `company.py`, `employee.py`, `file.py`, `finance.py`, `order.py`.

### Миграции Alembic — `server/alembic/versions/`

Хронологический порядок (по зависимостям `down_revision`):

1. `0001_initial` — пустая база
2. `53d39fbff4b7` — `employee`
3. `15393c8aa604` — `attendance_record`
4. `09cad9b7b635` — CHECK-ограничения и индексы посещений
5. `d11d6c3200d7` — `production_stage`, `orders`, `order_status_history`
6. `2ddff9ea949a` — `order_employee`
7. `b49be1c52e1c` — `order_file`
8. `353afd3c0c34` — `operating_expense`
9. `cbb57c3cf1f7` — `order_payment`, `order_expense`, `expense_category`
10. `2566be302171` — `is_closed`, `closed_at`, `closed_by` в `orders`
11. `e3a1f2b8c490` — `internal_number` обязательный и уникальный
12. `dd29ae32014b` — `delivery_lat/lon` в `orders`
13. `f4a8c1e9d2b7` — `company_settings`
14. `c7e2a4f9b1d6` — tier-1/tier-2 индексы производительности

### Тесты — `server/tests/`

| Файл | Что проверяет |
|---|---|
| `conftest.py` | Fixtures: `test_engine` (настоящий Postgres), `db` (транзакция с откатом), `client` (TestClient), `make_test_init_data()` |
| `test_auth.py` | HMAC-проверка initData, просроченный токен |
| `test_attendance.py` | toggle, двойной тап, подсчёт часов |
| `test_attendance_2b.py` | `patch_record()`, midnight rollover, discrepancies |
| `test_client_view.py` | Клиентский сериализатор не протекает (деньги, файлы, сотрудники) |
| `test_orders.py` | CRUD заказов, `public_code`, смена этапа |
| `test_order_employee.py` | Права рабочего: только по выданному заказу |
| `test_files.py` | Загрузка / скачивание файлов |
| `test_finance.py` | Платежи, расходы, CHECK по `to_employee` |
| `test_report.py` | Ежемесячный отчёт, отчёт по заказам, зарплатный отчёт |
| `test_company_settings.py` | Singleton company settings |
| `test_health.py` | `GET /api/health` |

### Скрипты — `server/scripts/`

| Файл | Что делает |
|---|---|
| `seed_catalog.py` | Заполнить справочник этапов производства |
| `seed_manager.py` | Добавить первого менеджера (`make seed-manager TG_ID=… NAME="…"`) |

---

## Фронтенд (`frontend/src/`)

### Инфраструктура

| Файл | Что это |
|---|---|
| `main.js` | Точка входа: Vue app, vue-i18n, монтирование `#app` |
| `App.vue` | Корневой компонент: аутентификация, определение роли, tab-роутинг, нижняя навигация; CSS-токены в `:root` |
| `api.js` | HTTP-клиент: `api.get/post/patch/delete`, `uploadFile` (XHR + прогресс), `fetchBlobUrl` |
| `telegram.js` | Обёртка над Telegram Mini App SDK: `initTelegram()`, `getInitData()`, `getColorScheme()`, `onThemeChange()` |
| `money.js` | Форматтер суммы в UZS |
| `i18n/index.js` | Настройка vue-i18n (`ru` по умолчанию) |
| `i18n/ru.js` / `i18n/uz.js` | Переводы интерфейса |

### Экраны (`frontend/src/views/`)

**Главная и посещения**

| Файл | Роль | Описание |
|---|---|---|
| `WorkerView.vue` | worker | Главная рабочего: кнопка отметки, список своих заказов |
| `HomeView.vue` | manager | Главная менеджера: сводка посещений, кнопки |
| `ManagerView.vue` | manager | Подэкран менеджера (список сотрудников, посещения) |
| `AttendanceCalendarView.vue` | manager | Календарь посещений по сотруднику |
| `EditVisitModal.vue` | manager | Редактирование записи посещения |

**Заказы**

| Файл | Описание |
|---|---|
| `OrdersView.vue` | Список заказов (фильтры, сортировка) |
| `OrderDetailView.vue` | Детальная карточка заказа + вкладки (файлы, история, финансы) |
| `OrderFormModal.vue` | Форма создания / редактирования заказа |
| `OrderFinanceTab.vue` | Вкладка: платежи и расходы по заказу |
| `StageChangeModal.vue` | Модалка смены производственного этапа |

**Финансы и отчёты**

| Файл | Описание |
|---|---|
| `TurnoverView.vue` | Оборот (таб верхнего уровня) |
| `FinanceDashboardView.vue` | Дашборд финансов: доходы vs расходы |
| `ReportsView.vue` | Выбор отчёта |
| `OrdersDetailReportView.vue` | Детальный отчёт по заказам за период |
| `EmployeeWagesView.vue` | Зарплатный отчёт по сотрудникам |
| `OperatingExpenseView.vue` | Список / добавление операционных расходов |

**Настройки и справочники**

| Файл | Описание |
|---|---|
| `SettingsView.vue` | Настройки: справочники + профиль компании |
| `CatalogPanel.vue` | CRUD этапов и категорий расходов |

**Компоненты**

| Файл | Описание |
|---|---|
| `components/LocationPicker.vue` | Карта Leaflet для выбора точки доставки |

---

## Ключевые инварианты — где они реализованы

| Инвариант | Слой | Файл |
|---|---|---|
| Один открытый визит на сотрудника | БД (partial unique index) | `attendance_record`, миграция `09cad9b7b635` |
| `to_employee` требует `employee_id` | БД (CHECK) | `order_expense`, миграция `cbb57c3cf1f7` |
| `company_settings` — singleton (id=1) | БД (CHECK) | `company.py`, миграция `f4a8c1e9d2b7` |
| `public_code` — случайный, неугадываемый | Сервис | `order.py` → `generate_public_code()` |
| Авторизация только через initData | API deps + security | `deps.py`, `security.py` |
| Клиентский сериализатор — whitelist | Сервис | `client_view.py` → `serialize_for_client()` |
| Деньги — `NUMERIC(12,2)` | Модели | все finance-модели |
| Цвета — только CSS-переменные | Frontend | `App.vue` (`:root`), `docs/color-system.md` |
