#!/usr/bin/env python3
"""Generate VITE_DEV_INIT_DATA for local frontend development.

Usage:
    python scripts/gen_dev_init_data.py [telegram_id]

Reads BOT_TOKEN from .env. Prints the generated initData string and also
writes it to .env.local (frontend/.env.local) for Vite to pick up.
"""
import hashlib
import hmac
import json
import sys
import time
from pathlib import Path
from urllib.parse import urlencode

import dotenv

ROOT = Path(__file__).resolve().parent.parent
dotenv.load_dotenv(ROOT / ".env")

import os  # noqa: E402

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
if not BOT_TOKEN:
    sys.exit("BOT_TOKEN not found in .env")

telegram_id = int(sys.argv[1]) if len(sys.argv) > 1 else 0
if telegram_id == 0:
    sys.exit("Usage: python scripts/gen_dev_init_data.py <telegram_id>")

user_json = json.dumps(
    {"id": telegram_id, "first_name": "Dev", "is_bot": False},
    separators=(",", ":"),
)
auth_date = str(int(time.time()))
raw = {"auth_date": auth_date, "user": user_json}
data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(raw.items()))

secret_key = hmac.new(
    key=b"WebAppData",
    msg=BOT_TOKEN.encode(),
    digestmod=hashlib.sha256,
)
hash_ = hmac.new(
    key=secret_key.digest(),
    msg=data_check_string.encode(),
    digestmod=hashlib.sha256,
).hexdigest()

init_data = urlencode({**raw, "hash": hash_})

env_local = ROOT / "frontend" / ".env.local"
lines = []
if env_local.exists():
    lines = [l for l in env_local.read_text().splitlines() if not l.startswith("VITE_DEV_INIT_DATA=")]
lines.append(f"VITE_DEV_INIT_DATA={init_data}")
env_local.write_text("\n".join(lines) + "\n")

print(f"Written to {env_local}")
print(f"telegram_id={telegram_id}, auth_date={auth_date}")
