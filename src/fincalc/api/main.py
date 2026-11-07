"""FastAPI application. JSON API under /api/v1, Swagger UI at /docs."""

from fastapi import APIRouter, FastAPI

from fincalc import __version__
from fincalc.api.routes import calculators, health

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
    return app


app = create_app()
