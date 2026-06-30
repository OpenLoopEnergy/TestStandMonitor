import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager

import dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

dotenv.load_dotenv()

from backend.db.database import init_db
from backend.services import data_store
from backend.services.csv_logger import run_logger
from backend.services.debug_logger import run_debug_logger
from backend.routes import data, settings, export, files, debug_export, backups, commands

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

    tasks = [
        asyncio.create_task(run_logger()),
        asyncio.create_task(run_debug_logger()),
        asyncio.create_task(run_pi_watchdog()),
    ]

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
app.include_router(backups.router)
app.include_router(debug_export.router)
app.include_router(commands.router)


@app.get("/health")
def health():
    return {"status": "ok", "pi_connected": data_store.latest.get("pi_connected", False)}


# ── Pi connection watchdog ────────────────────────────────────────────────────

_PI_TIMEOUT_SECONDS = 5  # Mark disconnected if no CAN frame received in this window


async def run_pi_watchdog():
    """Sets pi_connected based on whether CAN frames are arriving, not WebSocket state.
    Also computes and broadcasts CAN frame rate every 2 s."""
    _WATCHDOG_INTERVAL = 2
    while True:
        await asyncio.sleep(_WATCHDOG_INTERVAL)
        age = time.monotonic() - data_store.last_pi_frame_at
        currently_connected = data_store.latest.get("pi_connected", False)

        fps = round(data_store._frame_count / _WATCHDOG_INTERVAL, 1)
        data_store._frame_count = 0  # reset window

        updates: dict = {"pi_fps": fps}
        if age > _PI_TIMEOUT_SECONDS and currently_connected:
            updates["pi_connected"] = False
        elif age <= _PI_TIMEOUT_SECONDS and not currently_connected:
            updates["pi_connected"] = True

        await data_store.update(updates)


# ── WebSocket: Pi → Backend ───────────────────────────────────────────────────

@app.websocket("/ws/pi")
async def ws_pi(websocket: WebSocket):
    """
    The Raspberry Pi connects here and streams decoded CAN frames as JSON.
    Frame format: {"type": "frame", "data": {"s1": 1200, "tp": 1000, ...}}
    A keepalive is sent to the Pi every 25s to prevent Railway's proxy from
    timing out the connection due to no outbound traffic.
    """
    await websocket.accept()
    data_store.pi_connection = websocket
    logger.info("Pi connected from %s", websocket.client)

    async def send_keepalive():
        while True:
            await asyncio.sleep(15)
            try:
                await websocket.send_json({"type": "keepalive"})
            except Exception:
                break

    keepalive_task = asyncio.create_task(send_keepalive())

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
                if msg.get("type") == "frame" and isinstance(msg.get("data"), dict):
                    data_store.last_pi_frame_at = time.monotonic()
                    data_store._frame_count += 1
                    await data_store.update({**msg["data"], "pi_connected": True})
            except json.JSONDecodeError:
                logger.warning("Received non-JSON from Pi: %s", raw[:120])
    except WebSocketDisconnect:
        logger.warning("Pi disconnected")
    finally:
        keepalive_task.cancel()
        # Only clear if this is still the active connection — a fast reconnect
        # may have already stored a newer socket.
        if data_store.pi_connection is websocket:
            data_store.pi_connection = None


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
