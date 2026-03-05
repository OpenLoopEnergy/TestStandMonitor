"""
In-memory store for the latest decoded CAN signal values.

The Pi WebSocket handler writes here on every frame.
The frontend WebSocket handler reads from here to push to browsers.
Zero DB reads on the hot path.
"""
import asyncio
from typing import Any

# Latest signal values from the Pi — updated on every decoded CAN frame
latest: dict[str, Any] = {
    "s1": 0, "sp": 0, "tp": 0,
    "delay": 0, "trending": 0,
    "cycle": 0, "cycleTimer": 0,
    "lcSetpoint": 0, "lcRegulate": 0,
    "step": "Unknown",
    "t1": 0, "t3": 0,
    "f1": 0, "f2": 0, "f3": 0,
    "p1": 0, "p2": 0, "p3": 0, "p4": 0, "p5": 0,
    "pi_connected": False,
    "debug_mode": False,
    "tp_reved": 0,
    "m2_tp9a_dir": 0,
}

# Debug logging mode — when True, logs every tick in Automatic mode regardless of trending
debug_mode: bool = False

# All active frontend WebSocket connections
frontend_connections: set[Any] = set()

# Lock for thread-safe updates
_lock = asyncio.Lock()


async def update(data: dict[str, Any]) -> None:
    """Update the latest values and broadcast to all frontend clients."""
    async with _lock:
        latest.update(data)

    await broadcast(latest.copy())


async def broadcast(data: dict[str, Any]) -> None:
    """Push data to all connected frontend WebSocket clients."""
    dead: set[Any] = set()
    for ws in frontend_connections:
        try:
            await ws.send_json(data)
        except Exception:
            dead.add(ws)
    frontend_connections.difference_update(dead)
