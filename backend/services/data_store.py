"""
In-memory store for the latest decoded CAN signal values.

The Pi WebSocket handler writes here on every frame.
The frontend WebSocket handler reads from here to push to browsers.
Zero DB reads on the hot path.
"""
import asyncio
import time
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
    "debug_mode": True,
    "log_manual": False,
    "tp_reved": 0,
    "m2_tp9a_dir": 0,
    "ee_dir_switch": 0,
    # Machine state inputs (from 0x0CFF010A)
    "started": 0, "stopped": 0, "e_stopped": 0,
    "start_btn": 0, "stop_sw": 0, "estop_sw": 0,
    "tp_fwd": 0, "tp_rev": 0,
    # M1 command outputs (from 0x0CFF050A)
    "sol_a": 0, "sol_b": 0, "tp9a_enable": 0, "tp9a_dir": 0,
    # LC1 control loop (from 0x0CFF020A)
    "lc1": 0, "lc1_feedback": 0, "lc1_enable": 0, "lc1_state": 0,
    # SP circuit (from 0x0CFF030A)
    "sp_feedback": 0, "sp_enable": 0, "sp_regulate": 0, "sp_rev": 0,
    # M2 additional (from 0x0CFF0E14)
    "m2_pot": 0, "m2_tp9a": 0,
    # EE motor config (from 0x0CFF070A)
    "ee_sm_rpm": 0, "ee_sm_rate": 0, "ee_sm_timer": 0, "ee_cycle_delay": 0,
    # EE cycle profile (from 0x0CFF080A / 0x0CFF090A)
    "ee_cycle_time1": 0, "ee_cycle_time2": 0, "ee_cycle_time3": 0,
    "ee_cycle_time4": 0, "ee_cycle_time5": 0,
    "ee_cycle_psi1": 0, "ee_cycle_psi2": 0, "ee_cycle_psi3": 0,
    "ee_cycle_psi4": 0, "ee_cycle_psi5": 0,
    # Sensor scale factors (from 0x0CFF0A0A / 0x0CFF0B0A)
    "ee_t1_scale": 0, "ee_t3_scale": 0, "ee_f1_scale": 0, "ee_f2_scale": 0,
    "ee_f3_scale": 0, "ee_p1_scale": 0, "ee_p4_scale": 0, "ee_p5_scale": 0,
    # CAN frame rate (updated by pi watchdog every 2 s)
    "pi_fps": 0.0,
    # Debug log row counter — incremented by debug_logger, reset by /clear_debug_table
    "debug_rows_logged": 0,
    # M1 port diagnostics (from 0x0CFF110A)
    "m1_ports": {
        "sp_open": 0, "sp_short": 0,
        "sp_enable_open": 0, "sp_enable_short": 0,
        "sp_rev_open": 0, "sp_rev_short": 0,
        "tp_open": 0, "tp_short": 0,
        "tp_enable_open": 0, "tp_enable_short": 0,
        "tp_rev_open": 0, "tp_rev_short": 0,
        "lc1_open": 0, "lc1_short": 0,
        "lc1_pwr_open": 0, "lc1_pwr_short": 0,
        "led_open": 0, "led_short": 0,
        "m1_blink": 0,
    },
    # M2 port diagnostics (from 0x0CFF0F14)
    "m2_ports": {
        "polarity_open": 0, "polarity_short": 0,
        "stop_lamp_open": 0, "stop_lamp_short": 0,
        "sol_a_open": 0, "sol_a_short": 0,
        "sol_b_open": 0, "sol_b_short": 0,
        "tp9a_open": 0, "tp9a_short": 0,
        "tp9a_fwd_open": 0, "tp9a_fwd_short": 0,
        "tp9a_rev_open": 0, "tp9a_rev_short": 0,
        "m2_blink": 0,
        "supply_voltage": 0,
    },
}

# Timestamp of the last CAN frame received from the Pi (monotonic clock)
last_pi_frame_at: float = 0.0

# Raw frame counter — incremented by the Pi WS handler, reset by the watchdog every 2 s
_frame_count: int = 0

# Debug logging mode — when True, logs every tick in Automatic mode regardless of trending.
# Forced on permanently (no UI toggle) so automatic-test data is fully captured; the
# export filters back down to trending == 1 rows for graphing.
debug_mode: bool = True

# Log Manual mode — when True, also logs while the machine is in Manual mode (pb4 != 0)
log_manual: bool = False

# All active frontend WebSocket connections
frontend_connections: set[Any] = set()

# The single active Pi WebSocket connection — used to push commands down to the
# stand (start/stop/e-stop). None when no Pi is connected.
pi_connection: Any | None = None

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


async def send_to_pi(msg: dict[str, Any]) -> bool:
    """Push a message down to the connected Pi (e.g. a control command).

    Returns True if the message was sent, False if no Pi is connected or the
    send failed (in which case the stale connection is cleared)."""
    global pi_connection
    if pi_connection is None:
        return False
    try:
        await pi_connection.send_json(msg)
        return True
    except Exception:
        pi_connection = None
        return False
