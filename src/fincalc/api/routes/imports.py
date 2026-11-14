"""Import endpoints: upload -> preview (nothing saved) -> confirm."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session

from fincalc.core.transactions import Transaction
from fincalc.db.repository import Repository
from fincalc.db.session import get_session
from fincalc.importers.base import ImportFormatError
from fincalc.services import imports as svc

router = APIRouter(prefix="/imports", tags=["imports"])

SessionDep = Annotated[Session, Depends(get_session)]


class PreviewTransaction(BaseModel):
    line: int
    status: svc.RowStatus
    transaction: Transaction


class RowErrorOut(BaseModel):
    line: int
    code: str
    column: str
    value: str
    message: str


class SkippedRowOut(BaseModel):
    line: int
    broker_type: str


class PreviewOut(BaseModel):
    preview_id: str
    broker: str
    filename: str
    rows_total: int
    rows_new: int
    rows_duplicate: int
    rows_failed: int
    rows_skipped: int
    rows: list[PreviewTransaction]
    errors: list[RowErrorOut]
    skipped: list[SkippedRowOut]


class ImportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    broker: str
    filename: str
    imported_at: datetime
    rows_total: int
    rows_new: int
    rows_duplicate: int
    rows_failed: int


def preview_out(p: svc.ImportPreview) -> PreviewOut:
    return PreviewOut(
        preview_id=p.id,
        broker=p.broker,
        filename=p.filename,
        rows_total=p.rows_total,
        rows_new=p.rows_new,
        rows_duplicate=p.rows_duplicate,
        rows_failed=len(p.errors),
        rows_skipped=len(p.skipped),
        rows=[
            PreviewTransaction(line=r.line, status=r.status, transaction=r.transaction)
            for r in p.rows
        ],
        errors=[RowErrorOut(**e.__dict__) for e in p.errors],
        skipped=[SkippedRowOut(**s.__dict__) for s in p.skipped],
    )


async def read_upload(file: UploadFile) -> bytes:
    data = await file.read(svc.MAX_UPLOAD_BYTES + 1)
    if len(data) > svc.MAX_UPLOAD_BYTES:
        raise HTTPException(413, "file too large (max 5 MB)")
    return data


@router.post("/{broker}/preview", summary="Upload a statement and preview it (saves nothing)")
async def preview(broker: str, file: UploadFile, session: SessionDep) -> PreviewOut:
    data = await read_upload(file)
    try:
        p = svc.create_preview(Repository(session), broker, file.filename or "upload.csv", data)
    except svc.UnknownBrokerError:
        raise HTTPException(404, f"unknown broker: {broker}") from None
    except ImportFormatError as exc:
        raise HTTPException(422, str(exc)) from None
    return preview_out(p)


@router.post("/{preview_id}/confirm", summary="Save the new transactions of a preview")
def confirm(preview_id: str, session: SessionDep) -> ImportOut:
    try:
        record = svc.confirm_preview(Repository(session), preview_id)
    except svc.PreviewNotFoundError:
        raise HTTPException(404, "preview not found or expired") from None
    return ImportOut.model_validate(record)


@router.get("", summary="Import log (newest first)")
def list_imports(session: SessionDep) -> list[ImportOut]:
    return [ImportOut.model_validate(r) for r in Repository(session).list_imports()]
