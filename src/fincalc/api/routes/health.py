"""Health check for Docker."""

from fastapi import APIRouter
from pydantic import BaseModel

from fincalc import __version__

router = APIRouter(tags=["system"])


class Health(BaseModel):
    status: str
    version: str


@router.get("/health", summary="Liveness check")
def health() -> Health:
    return Health(status="ok", version=__version__)
