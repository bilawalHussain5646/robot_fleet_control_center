import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import api
from app.core.config import settings
from app.db.session import Base, engine, SessionLocal
from app.services.seed import seed
from app.simulation.simulator import simulation_loop
from app.websocket.manager import manager
app=FastAPI(title="Robot Fleet Control Center API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.cors_origins.split(',')], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(api)
@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine); db=SessionLocal(); seed(db, settings.simulation_robot_count); db.close()
    if settings.simulation_enabled: asyncio.create_task(simulation_loop())
@app.websocket("/ws/fleet")
async def fleet_ws(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True: await ws.receive_text()
    except WebSocketDisconnect: manager.disconnect(ws)
