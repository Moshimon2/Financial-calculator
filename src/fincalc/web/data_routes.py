"""HTML pages backed by the database: transactions list and CSV import."""

from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session
from starlette.datastructures import UploadFile as StarletteUploadFile

from fincalc.core.transactions import TransactionType
from fincalc.db.repository import Repository, TransactionFilter
from fincalc.db.session import get_session
from fincalc.importers.base import ImportFormatError
from fincalc.services import imports as svc
from fincalc.settings import display_timezone
from fincalc.web.i18n.hu import TEXTS
from fincalc.web.routes import templates

router = APIRouter(include_in_schema=False)

SessionDep = Annotated[Session, Depends(get_session)]
PAGE_SIZE = 50


def _local_day_start(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=display_timezone()).astimezone(UTC)


@router.get("/transactions", name="transactions")
def transactions_page(
    request: Request,
    session: SessionDep,
    date_from: str = "",
    date_to: str = "",
    ticker: str = "",
    type: str = "",
    page: int = 1,
) -> HTMLResponse:
    texts = TEXTS["transactions"]
    errors: list[str] = []
    flt_from = flt_to = None
    tx_type = None
    try:
        if date_from:
            flt_from = _local_day_start(date.fromisoformat(date_from))
    except ValueError:
        errors.append(texts["invalid_filter"].format(field=texts["filter"]["date_from"]))
    try:
        if date_to:  # inclusive day in the UI -> exclusive next-day start
            flt_to = _local_day_start(date.fromisoformat(date_to) + timedelta(days=1))
    except ValueError:
        errors.append(texts["invalid_filter"].format(field=texts["filter"]["date_to"]))
    try:
        if type:
            tx_type = TransactionType(type)
    except ValueError:
        errors.append(texts["invalid_filter"].format(field=texts["filter"]["type"]))

    page = max(page, 1)
    result = Repository(session).list_transactions(
        TransactionFilter(
            date_from=flt_from, date_to=flt_to, ticker=ticker.strip() or None, type=tx_type
        ),
        limit=PAGE_SIZE,
        offset=(page - 1) * PAGE_SIZE,
    )
    pages = max(1, -(-result.total // PAGE_SIZE))
    filters = {"date_from": date_from, "date_to": date_to, "ticker": ticker, "type": type}
    context: dict[str, Any] = {
        "page": "transactions",
        "result": result,
        "filters": filters,
        "current_page": page,
        "pages": pages,
        "filter_errors": errors,
        "query": lambda p: str(
            request.url.include_query_params(**{k: v for k, v in filters.items()}, page=p)
        ),
        "types": list(TransactionType),
    }
    return templates.TemplateResponse(request, "transactions.html", context)


def _import_log(session: Session) -> dict[str, Any]:
    return {"imports": Repository(session).list_imports()}


@router.get("/import", name="import")
def import_page(request: Request, session: SessionDep) -> HTMLResponse:
    context = {"page": "import"} | _import_log(session)
    return templates.TemplateResponse(request, "import.html", context)


@router.post("/import/preview")
async def import_preview(request: Request, session: SessionDep) -> HTMLResponse:
    texts = TEXTS["import"]
    form = await request.form()
    upload = form.get("file")
    message: str | None = None
    preview = None
    if not isinstance(upload, StarletteUploadFile) or not upload.filename:
        message = texts["no_file"]
    else:
        data = await upload.read(svc.MAX_UPLOAD_BYTES + 1)
        await upload.close()
        if len(data) > svc.MAX_UPLOAD_BYTES:
            message = texts["too_large"]
        else:
            try:
                preview = svc.create_preview(
                    Repository(session), "lightyear", upload.filename, data
                )
            except ImportFormatError as exc:
                message = texts["format_error"].format(message=exc)
    context = {"preview": preview, "message": message}
    return templates.TemplateResponse(request, "import/_preview.html", context)


@router.post("/import/{preview_id}/confirm")
def import_confirm(request: Request, preview_id: str, session: SessionDep) -> HTMLResponse:
    try:
        record = svc.confirm_preview(Repository(session), preview_id)
    except svc.PreviewNotFoundError:
        record = None
    context = {"record": record} | _import_log(session)
    return templates.TemplateResponse(request, "import/_confirmed.html", context)
