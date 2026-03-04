import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager

import dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

dotenv.load_dotenv()

from backend.db.database import init_db
from backend.services import data_store
from backend.services.csv_logger import run_logger
from backend.routes import data, settings, export, files

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initialising database…")
    init_db()

    logger.info("Starting background CSV logger…")
    logger.info("Starting sim mode if MOCK_MODE=true…")

    tasks = [asyncio.create_task(run_logger())]

    if os.getenv("MOCK_MODE", "false").lower() == "true":
        from pi.sim_mode import run_sim
        tasks.append(asyncio.create_task(run_sim()))

    yield  # App running

    # Shutdown — cancel background tasks cleanly
    for t in tasks:
        t.cancel()
        try:
            await t
        except asyncio.CancelledError:
            pass


app = FastAPI(title="Test Stand API", lifespan=lifespan)

# Allow the React dev server (and production Vercel domain) to call the API
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ALLOWED_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST routes
app.include_router(data.router)
app.include_router(settings.router)
app.include_router(export.router)
app.include_router(files.router)


@app.get("/health")
def health():
    return {"status": "ok", "pi_connected": data_store.latest.get("pi_connected", False)}


# ── WebSocket: Pi → Backend ───────────────────────────────────────────────────

@app.websocket("/ws/pi")
async def ws_pi(websocket: WebSocket):
    """
    The Raspberry Pi connects here and streams decoded CAN frames as JSON.
    Frame format: {"type": "frame", "data": {"s1": 1200, "tp": 1000, ...}}
    """
    await websocket.accept()
    logger.info("Pi connected from %s", websocket.client)
    await data_store.update({"pi_connected": True})

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
                if msg.get("type") == "frame" and isinstance(msg.get("data"), dict):
                    await data_store.update(msg["data"])
            except json.JSONDecodeError:
                logger.warning("Received non-JSON from Pi: %s", raw[:120])
    except WebSocketDisconnect:
        logger.warning("Pi disconnected")
    finally:
        await data_store.update({"pi_connected": False})


# ── WebSocket: Backend → Browser ─────────────────────────────────────────────

@app.websocket("/ws/frontend")
async def ws_frontend(websocket: WebSocket):
    """
    Browser clients connect here to receive live data pushed from the Pi.
    On connect, sends the current snapshot immediately.
    """
    await websocket.accept()
    data_store.frontend_connections.add(websocket)
    logger.debug("Frontend client connected (%d total)", len(data_store.frontend_connections))

    # Send current state immediately so the UI doesn't wait for the next CAN frame
    try:
        await websocket.send_json(data_store.latest.copy())
    except Exception:
        pass

    try:
        # Keep connection alive — client messages are ignored (read-only feed)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        data_store.frontend_connections.discard(websocket)
        logger.debug("Frontend client disconnected (%d remaining)", len(data_store.frontend_connections))
