"""FastAPI application. JSON API under /api/v1, Swagger UI at /docs."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.staticfiles import StaticFiles

from fincalc import __version__
from fincalc.api.routes import calculators, health, transactions
from fincalc.db.migrate import upgrade_to_head
from fincalc.db.session import database_url, ensure_sqlite_writable
from fincalc.settings import auto_migrate
from fincalc.web.routes import STATIC_DIR
from fincalc.web.routes import router as web_router

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    ensure_sqlite_writable(database_url())
    if auto_migrate():
        upgrade_to_head()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        lifespan=lifespan,
        title="fincalc API",
        version=__version__,
        description=(
            "Financial calculators for Hungarian investors: compound interest, inflation, "
            "ETF costs (TER) and TBSZ. Money values are decimals serialised as strings "
            "and are not rounded."
        ),
    )
    api = APIRouter(prefix=API_PREFIX)
    api.include_router(health.router)
    api.include_router(calculators.router)
    api.include_router(transactions.router)
    app.include_router(api)
    app.include_router(web_router)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


app = create_app()
