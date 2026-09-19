from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app import seed
from app.modules.qr_ticket import TicketError
from app.routers import api

app = FastAPI(title="Metrofare", version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(TicketError)
def _ticket_error(_: Request, exc: TicketError):
    return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})


@app.on_event("startup")
def _startup():
    seed.init_db()

app.include_router(api)

@app.get("/api/health")
def health():
    return {"ok": True, "project": "metrofare"}
