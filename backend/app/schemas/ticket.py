from pydantic import BaseModel


class TicketIssueRequest(BaseModel):
    run_id: int


class TicketVoidRequest(BaseModel):
    reason: str
