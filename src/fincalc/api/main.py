"""FastAPI application. JSON API under /api/v1, Swagger UI at /docs."""

from fastapi import APIRouter, FastAPI
from fastapi.staticfiles import StaticFiles

from fincalc import __version__
from fincalc.api.routes import calculators, health
from fincalc.web.routes import STATIC_DIR
from fincalc.web.routes import router as web_router

API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    app = FastAPI(
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
    app.include_router(api)
    app.include_router(web_router)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


app = create_app()
