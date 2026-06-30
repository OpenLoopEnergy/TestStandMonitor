"""
Control commands — start / stop / emergency-stop.

The browser POSTs a symbolic action here; we forward it down the Pi WebSocket
as {"type": "command", "action": ...}. The Pi owns the CAN byte layout, so this
endpoint stays protocol-agnostic. Physical panel buttons are unaffected — they
are read in on a separate CAN ID and never touch this path.
"""
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services import data_store

router = APIRouter()
logger = logging.getLogger(__name__)

# Actions the frontend is allowed to issue. The Pi maps these to CAN frames.
ALLOWED_ACTIONS = {"start", "stop", "estop"}


class CommandRequest(BaseModel):
    action: str


@router.post("/command")
async def send_command(req: CommandRequest):
    action = req.action
    if action not in ALLOWED_ACTIONS:
        raise HTTPException(status_code=422, detail=f"Unknown action: {action}")

    # Don't send commands into the void — surface a clear "Pi offline" error.
    if not data_store.latest.get("pi_connected", False):
        raise HTTPException(status_code=409, detail="Pi is offline — command not sent.")

    sent = await data_store.send_to_pi({"type": "command", "action": action})
    if not sent:
        raise HTTPException(status_code=503, detail="Failed to reach the Pi.")

    logger.info("Command sent to Pi: %s", action)
    return {"status": "sent", "action": action}
