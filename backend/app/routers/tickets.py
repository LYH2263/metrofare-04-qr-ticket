from fastapi import APIRouter, HTTPException

from app.modules.qr_ticket import TicketError
from app.schemas.ticket import TicketIssueRequest, TicketVoidRequest
from app.services.metro_service import MetroService

router = APIRouter(tags=["qr-tickets"])


def _call(action, *args):
    try:
        with MetroService() as s:
            return action(s, *args)
    except TicketError as e:
        raise HTTPException(status_code=e.status, detail=str(e))


@router.get("/tickets")
def list_tickets():
    # Voided tickets are hidden from the default list.
    return {"items": _call(lambda s: s.tickets())}


@router.post("/tickets/issue")
def issue_ticket(body: TicketIssueRequest):
    return _call(lambda s: s.issue_ticket(body.run_id))


@router.get("/tickets/{code}")
def verify_ticket(code: str):
    # Lookup by code doubles as verification; a voided code still returns,
    # complete with its void reason.
    return _call(lambda s: s.verify_ticket(code))


@router.post("/tickets/{code}/void")
def void_ticket(code: str, body: TicketVoidRequest):
    return _call(lambda s: s.void_ticket(code, body.reason))
