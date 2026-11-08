"""Read-only transaction endpoints."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session

from fincalc.core.transactions import TransactionType
from fincalc.db.repository import Repository, TransactionFilter
from fincalc.db.session import get_session

router = APIRouter(prefix="/transactions", tags=["transactions"])

SessionDep = Annotated[Session, Depends(get_session)]


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    broker: str
    external_id: str | None
    type: TransactionType
    executed_at: datetime
    ticker: str | None
    isin: str | None
    quantity: Decimal | None
    price: Decimal | None
    amount: Decimal
    fee: Decimal
    currency: str
    import_id: int


class TransactionPage(BaseModel):
    items: list[TransactionOut]
    total: int
    limit: int
    offset: int


@router.get("", summary="List transactions (newest first)")
def list_transactions(
    session: SessionDep,
    date_from: Annotated[datetime | None, Query(description="Inclusive, ISO 8601")] = None,
    date_to: Annotated[datetime | None, Query(description="Exclusive, ISO 8601")] = None,
    ticker: str | None = None,
    type: TransactionType | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TransactionPage:
    for value in (date_from, date_to):
        if value is not None and value.tzinfo is None:
            raise HTTPException(422, "date_from/date_to must include a timezone (e.g. Z)")
    page = Repository(session).list_transactions(
        TransactionFilter(date_from=date_from, date_to=date_to, ticker=ticker, type=type),
        limit=limit,
        offset=offset,
    )
    return TransactionPage(
        items=[TransactionOut.model_validate(t) for t in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/latest", summary="Latest purchase")
def latest_purchase(session: SessionDep) -> TransactionOut:
    latest = Repository(session).latest_purchase()
    if latest is None:
        raise HTTPException(404, "No purchases yet")
    return TransactionOut.model_validate(latest)
