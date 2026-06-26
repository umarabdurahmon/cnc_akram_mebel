# Деплой на DigitalOcean Droplet (без Docker)

После первоначальной настройки CI/CD (GitHub Actions) будет автоматически
обновлять прод при каждом пуше в `master`.

---

## 1. Создание Droplet

- **OS:** Ubuntu 24.04 LTS
- **RAM:** минимум 1 GB (рекомендуется 2 GB)
- **Диск:** минимум 25 GB
- Регион на выбор; добавь SSH-ключ своего ноутбука при создании

---

## 2. Базовые пакеты

```bash
ssh root@<DROPLET_IP>

apt update && apt upgrade -y
apt install -y git curl python3.12 python3.12-venv python3-pip nginx certbot
```

---

## 3. PostgreSQL 16

```bash
apt install -y postgresql-16

# Создать пользователя и базу
sudo -u postgres psql << 'EOF'
CREATE USER furniture WITH PASSWORD 'замени_на_сложный_пароль';
CREATE DATABASE furniture OWNER furniture;
EOF
```

---

## 4. Пользователь deployer

CI/CD подключается под отдельным пользователем без root-доступа.

```bash
useradd -m -s /bin/bash deployer
usermod -aG sudo deployer

# SSH-ключ для GitHub Actions
sudo -u deployer bash -c '
  mkdir -p ~/.ssh && chmod 700 ~/.ssh
  ssh-keygen -t ed25519 -f ~/.ssh/github_deploy -N ""
  cat ~/.ssh/github_deploy.pub >> ~/.ssh/authorized_keys
  chmod 600 ~/.ssh/authorized_keys
'

# Скопируй приватный ключ — он пойдёт в DROPLET_SSH_KEY секрет GitHub
cat /home/deployer/.ssh/github_deploy
```

Разрешить deployer перезапускать только нужные сервисы без пароля:

```bash
cat > /etc/sudoers.d/deployer-services << 'EOF'
deployer ALL=(ALL) NOPASSWD: \
  /bin/systemctl restart cnc-api, \
  /bin/systemctl restart cnc-bot, \
  /bin/systemctl restart cnc-client-bot, \
  /bin/systemctl start cnc-api, \
  /bin/systemctl start cnc-bot, \
  /bin/systemctl start cnc-client-bot, \
  /bin/systemctl stop cnc-api, \
  /bin/systemctl stop cnc-bot, \
  /bin/systemctl stop cnc-client-bot
EOF
chmod 440 /etc/sudoers.d/deployer-services
```

---

## 5. SSH Deploy Key (Droplet → GitHub)

```bash
sudo -u deployer ssh-keygen -t ed25519 -f /home/deployer/.ssh/github_repo -N "" -C "cnc-mebel-droplet"

cat /home/deployer/.ssh/github_repo.pub  # добавить в GitHub → Settings → Deploy keys

sudo -u deployer bash -c 'cat > /home/deployer/.ssh/config << EOF
Host github.com
    IdentityFile ~/.ssh/github_repo
    StrictHostKeyChecking no
EOF
chmod 600 /home/deployer/.ssh/config'

# Проверить
sudo -u deployer ssh -T git@github.com
```

Добавь публичный ключ в GitHub:
**Репозиторий → Settings → Deploy keys → Add deploy key** (Allow write access: не ставить)

---

## 6. GitHub Secrets

**Settings → Secrets and variables → Actions → New repository secret**

| Secret | Значение |
|---|---|
| `DROPLET_HOST` | IP-адрес Droplet |
| `DROPLET_USER` | `deployer` |
| `DROPLET_SSH_KEY` | содержимое `~/.ssh/github_deploy` (приватный ключ) |
| `DROPLET_PORT` | `22` |

---

## 7. Клонирование репозитория

```bash
mkdir -p /opt/cnc_mebel_bot
chown deployer:deployer /opt/cnc_mebel_bot

sudo -u deployer git clone git@github.com:umarabdurahmon/cnc_mebel_bot.git /opt/cnc_mebel_bot
```

---

## 8. Python venv и зависимости

```bash
cd /opt/cnc_mebel_bot

sudo -u deployer python3.12 -m venv venv
sudo -u deployer venv/bin/pip install -e "server/." -q
```

---

## 9. Создание .env

```bash
cp /opt/cnc_mebel_bot/.env.example /opt/cnc_mebel_bot/.env
chown deployer:deployer /opt/cnc_mebel_bot/.env
chmod 600 /opt/cnc_mebel_bot/.env
nano /opt/cnc_mebel_bot/.env
```

Минимальный набор:

```dotenv
POSTGRES_DB=furniture
POSTGRES_USER=furniture
POSTGRES_PASSWORD=<сложный_пароль — тот же что в п.3>
DATABASE_URL=postgresql+psycopg://furniture:<пароль>@localhost:5432/furniture

BOT_TOKEN=<токен_бота_сотрудников>
CLIENT_BOT_TOKEN=<токен_клиентского_бота>

MINIAPP_URL=https://cnc.factorymanagement.uz
CORS_ORIGINS=https://cnc.factorymanagement.uz

STORAGE_ROOT=/opt/cnc_mebel_bot/storage
SHOP_TZ=Asia/Tashkent
```

Создать директорию для файлов заказов:

```bash
mkdir -p /opt/cnc_mebel_bot/storage
chown deployer:deployer /opt/cnc_mebel_bot/storage
```

---

## 10. Применить миграции и создать менеджера

```bash
cd /opt/cnc_mebel_bot/server

sudo -u deployer /opt/cnc_mebel_bot/venv/bin/alembic upgrade head

# Создать первого менеджера
sudo -u deployer /opt/cnc_mebel_bot/venv/bin/python \
  scripts/seed_manager.py --tg-id <TELEGRAM_ID> --name "Имя Фамилия"
```

---

## 11. Systemd сервисы

```bash
# Скопировать unit-файлы из репозитория
cp /opt/cnc_mebel_bot/deploy/cnc-api.service        /etc/systemd/system/
cp /opt/cnc_mebel_bot/deploy/cnc-bot.service        /etc/systemd/system/
cp /opt/cnc_mebel_bot/deploy/cnc-client-bot.service /etc/systemd/system/

systemctl daemon-reload

systemctl enable cnc-api cnc-bot cnc-client-bot
systemctl start  cnc-api cnc-bot cnc-client-bot

# Проверить статус
systemctl status cnc-api cnc-bot cnc-client-bot
```

---

## 12. SSL-сертификат (Let's Encrypt)

> Сначала SSL, потом nginx — иначе nginx не запустится без сертификата.

Убедись что DNS домена указывает на Droplet (`dig @8.8.8.8 cnc.factorymanagement.uz +short`).

```bash
mkdir -p /var/www/certbot

# Standalone-режим: certbot поднимает временный сервер на порту 80
certbot certonly --standalone \
  -d cnc.factorymanagement.uz \
  --email abdurahmon.umar.me@gmail.com \
  --agree-tos --no-eff-email
```

Автообновление:

```bash
crontab -e
# Добавь строку:
0 3 * * * certbot renew --quiet --deploy-hook "systemctl reload nginx"
```

---

## 13. Nginx

```bash
# Подключить конфиг из репозитория
ln -s /opt/cnc_mebel_bot/nginx/nginx.conf /etc/nginx/sites-available/cnc
ln -s /etc/nginx/sites-available/cnc /etc/nginx/sites-enabled/cnc

# Убрать дефолтный конфиг если есть
rm -f /etc/nginx/sites-enabled/default

# Проверить и запустить
nginx -t
systemctl enable nginx
systemctl start nginx
```

Проверить что всё работает:

```bash
curl https://cnc.factorymanagement.uz/api/health
```

---

## 14. BotFather — обновить URL Mini App

```
@BotFather → /setmenubutton → выбери бота → URL: https://cnc.factorymanagement.uz
```

---

## 15. Полезные команды

```bash
# Логи сервисов
journalctl -u cnc-api -f
journalctl -u cnc-bot -f
journalctl -u cnc-client-bot -f

# Перезапустить сервис
systemctl restart cnc-api

# Статус всех трёх
systemctl status cnc-api cnc-bot cnc-client-bot

# Применить миграцию вручную
cd /opt/cnc_mebel_bot/server
sudo -u deployer /opt/cnc_mebel_bot/venv/bin/alembic upgrade head

# Размер хранилища файлов
du -sh /opt/cnc_mebel_bot/storage
```

---

## CI/CD — как это работает

При каждом пуше в `master`:
1. GitHub Actions запускает CI: lint + mypy + тесты + сборка фронтенда
2. Если CI зелёный — копирует собранный фронтенд на Droplet через scp
3. SSH: `git pull` → `pip install` → `alembic upgrade head` → `systemctl restart`

Время деплоя: ~1–2 минуты.
