"""FastAPI Application Entry Point for D-Fleet."""

from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import router as api_router
from app.api.websocket import telemetry_hub
from app.communication.websocket_adapter import p2p_ws_adapter
from app.database.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database tables
    init_db()
    yield
    # Shutdown


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="D-Fleet: Decentralized Multi-Robot Warehouse Coordination Simulator API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount REST API routes
app.include_router(api_router)


@app.get("/")
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "mode": "decentralized-simulation",
        "docs": "/docs",
    }


# Dashboard Telemetry WebSocket Channel
@app.websocket("/ws/simulation")
async def websocket_simulation_telemetry(websocket: WebSocket):
    await telemetry_hub.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await telemetry_hub.handle_inbound_message(websocket, data)
    except WebSocketDisconnect:
        await telemetry_hub.disconnect(websocket)
    except Exception:
        await telemetry_hub.disconnect(websocket)


# Robot-to-Robot P2P WebSocket Channel
@app.websocket("/ws/p2p/{robot_id}")
async def websocket_p2p_endpoint(websocket: WebSocket, robot_id: str):
    await p2p_ws_adapter.connect(robot_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # P2P messages are parsed and routed directly to destination peer
            # Passive routing only - no central decision making
            pass
    except WebSocketDisconnect:
        await p2p_ws_adapter.disconnect(robot_id)
    except Exception:
        await p2p_ws_adapter.disconnect(robot_id)
