from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.attendance import router as attendance_router
from app.api.categories import router as categories_router
from app.api.company import router as company_router
from app.api.employees import router as employees_router
from app.api.files import router as files_router
from app.api.finance import router as finance_router
from app.api.health import router as health_router
from app.api.me import router as me_router
from app.api.operating_expenses import router as operating_expenses_router
from app.api.orders import router as orders_router
from app.api.stages import router as stages_router
from app.core.config import settings

app = FastAPI(title="CNC Mebel API")

# Fail fast: the entire auth layer relies on bot_token for HMAC verification.
# Running without a token would accept any crafted initData.
if not settings.bot_token:
    raise RuntimeError(
        "BOT_TOKEN is not set. "
        "The API cannot start without it — the auth layer requires it for HMAC verification."
    )

_cors_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
if _cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

app.include_router(health_router, prefix="/api")
app.include_router(me_router, prefix="/api")
app.include_router(attendance_router, prefix="/api")
app.include_router(stages_router, prefix="/api")
app.include_router(orders_router, prefix="/api")
app.include_router(files_router, prefix="/api")
app.include_router(employees_router, prefix="/api")
app.include_router(categories_router, prefix="/api")
app.include_router(finance_router, prefix="/api")
app.include_router(operating_expenses_router, prefix="/api")
app.include_router(company_router, prefix="/api")
