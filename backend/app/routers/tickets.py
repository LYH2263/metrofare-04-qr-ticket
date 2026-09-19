from fastapi import APIRouter
from pydantic import BaseModel

from app.services.metro_service import MetroService

router = APIRouter(tags=["tickets"])


class IssueRequest(BaseModel):
    run_id: int


class VerifyRequest(BaseModel):
    code: str


class VoidRequest(BaseModel):
    reason: str = ""


@router.post("/tickets", status_code=201)
def issue_ticket(body: IssueRequest):
    with MetroService() as s:
        return s.issue_ticket(body.run_id)


@router.get("/tickets")
def list_tickets(include_voided: bool = False):
    with MetroService() as s:
        return {"items": s.tickets(include_voided)}


@router.get("/tickets/{code}")
def get_ticket(code: str):
    with MetroService() as s:
        return s.ticket(code)


@router.post("/tickets/verify")
def verify_ticket(body: VerifyRequest):
    with MetroService() as s:
        return s.verify_ticket(body.code)


@router.post("/tickets/{code}/void")
def void_ticket(code: str, body: VoidRequest):
    with MetroService() as s:
        return s.void_ticket(code, body.reason)
