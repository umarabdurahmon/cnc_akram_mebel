# Furniture System — команды разработки.
# Цель Makefile: дать единую команду проверки (make check), которую Claude Code
# гоняет перед тем, как сказать "готово".
#
# Перед первым запуском: make install

VENV    := server/.venv
BIN     := $(VENV)/bin
PYTHON  := $(BIN)/python

.PHONY: help install up down logs check lint format test front-build migrate revision seed-manager seed-catalog dev-api dev-bot dev-clientbot dev-front

help:
	@echo "install    — создать venv и установить зависимости"
	@echo "up         — поднять Postgres (docker compose)"
	@echo "down       — остановить контейнеры"
	@echo "check      — полная проверка: lint + типы + тесты + сборка фронта"
	@echo "lint       — ruff + mypy (бэкенд)"
	@echo "test       — pytest против тестовой БД"
	@echo "migrate    — применить миграции Alembic"
	@echo "revision   — новая миграция: make revision m=\"описание\""
	@echo "dev-api        — запустить FastAPI (uvicorn, reload)"
	@echo "dev-bot        — запустить бота сотрудников (aiogram, long-polling)"
	@echo "dev-clientbot  — запустить клиентский бот (aiogram, long-polling)"
	@echo "dev-front      — запустить Vite (Mini App)"

install:
	python3.12 -m venv $(VENV)
	$(BIN)/pip install -e "server/.[dev]"
	cd frontend && npm install

up:
	docker compose up -d postgres

down:
	docker compose down

logs:
	docker compose logs -f postgres

# --- Петля верификации ---
check: lint test front-build

lint:
	cd server && $(CURDIR)/$(BIN)/ruff check . && $(CURDIR)/$(BIN)/ruff format --check . && $(CURDIR)/$(BIN)/mypy app

format:
	cd server && $(CURDIR)/$(BIN)/ruff format . && $(CURDIR)/$(BIN)/ruff check --fix .

test:
	cd server && $(CURDIR)/$(BIN)/pytest

front-build:
	cd frontend && npm run lint && npm run build

# --- Миграции ---
migrate:
	cd server && $(CURDIR)/$(BIN)/alembic upgrade head

revision:
	@test -n "$(m)" || (echo "Укажи сообщение: make revision m=\"...\"" && exit 1)
	cd server && $(CURDIR)/$(BIN)/alembic revision --autogenerate -m "$(m)"

# --- Сид данных ---
seed-manager:
	@test -n "$(TG_ID)" || (echo "Укажи TG_ID: make seed-manager TG_ID=123 NAME=\"Имя Фамилия\"" && exit 1)
	@test -n "$(NAME)" || (echo "Укажи NAME: make seed-manager TG_ID=123 NAME=\"Имя Фамилия\"" && exit 1)
	$(PYTHON) server/scripts/seed_manager.py --tg-id $(TG_ID) --name "$(NAME)"

seed-catalog:
	$(PYTHON) server/scripts/seed_catalog.py

# --- Запуск процессов ---
dev-api:
	cd server && $(CURDIR)/$(BIN)/uvicorn app.main:app --reload --port 8000

dev-bot:
	cd server && $(CURDIR)/$(PYTHON) -m bot.main

dev-clientbot:
	cd server && $(CURDIR)/$(PYTHON) -m bot.client_bot

dev-front:
	cd frontend && npm run dev
