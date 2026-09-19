from fastapi import APIRouter

from app.routers import dashboard, edges, fares, history, quote, settings, stations, tickets

api = APIRouter(prefix="/api")
for r in (dashboard, stations, edges, fares, quote, history, settings, tickets):
    api.include_router(r.router)
