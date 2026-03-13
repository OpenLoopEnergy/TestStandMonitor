"""
Raspberry Pi CAN publisher.

Reads frames from can0 via python-can, decodes them, and streams
live signal updates to the cloud backend over a WebSocket connection.

Usage:
    BACKEND_WS_URL=wss://your-app.railway.app/ws/pi python can_publisher.py

The script reconnects automatically if the WebSocket drops.
"""
import asyncio
import json
import logging
import os

import can
import websockets

from can_decoder import decode_message, decoded_to_live_frame

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s — %(message)s",
)
logger = logging.getLogger(__name__)

BACKEND_WS_URL = os.environ["BACKEND_WS_URL"]  # Required — fail fast if missing
CAN_CHANNEL = os.getenv("CAN_CHANNEL", "can0") # test
RECONNECT_DELAY = 2  # seconds between reconnection attempts


async def publish_can_frames(ws):
    """Read CAN frames and send decoded live updates to the backend."""
    bus = can.interface.Bus(channel=CAN_CHANNEL, bustype="socketcan")
    logger.info("Connected to CAN interface on %s", CAN_CHANNEL)

    async def drain_incoming():
        """Discard any messages sent by the backend (e.g. keepalives)."""
        try:
            async for _ in ws:
                pass
        except Exception:
            pass

    drain_task = asyncio.create_task(drain_incoming())
    loop = asyncio.get_event_loop()

    try:
        while True:
            # Run blocking bus.recv() in a thread so the event loop stays free
            msg = await loop.run_in_executor(None, lambda: bus.recv(timeout=1))
            if msg is None:
                continue  # Timeout — keep waiting

            msg_id, decoded = decode_message({
                "arbitration": msg.arbitration_id,
                "data": list(msg.data),
                "timestamp": msg.timestamp,
            })

            if not decoded or decoded == 0:
                continue

            live_frame = decoded_to_live_frame(decoded)
            if live_frame is None:
                continue

            await ws.send(json.dumps({"type": "frame", "data": live_frame}))

    except can.CanError as e:
        logger.error("CAN bus error: %s", e)
    finally:
        drain_task.cancel()
        bus.shutdown()


async def main():
    while True:
        try:
            logger.info("Connecting to backend at %s", BACKEND_WS_URL)
            async with websockets.connect(BACKEND_WS_URL, ping_interval=None) as ws:
                logger.info("WebSocket connected — streaming CAN data")
                await publish_can_frames(ws)
        except (websockets.WebSocketException, OSError) as e:
            logger.warning("Connection lost: %s — reconnecting in %ds", e, RECONNECT_DELAY)
        except Exception:
            logger.exception("Unexpected error — reconnecting in %ds", RECONNECT_DELAY)

        await asyncio.sleep(RECONNECT_DELAY)


if __name__ == "__main__":
    asyncio.run(main())
