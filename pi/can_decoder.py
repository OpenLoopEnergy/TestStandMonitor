"""
CAN frame decoder — preserved logic from the original decodeAndProcess.py.

decode_message(message) accepts:
  {"arbitration": int, "data": list[int], "timestamp": float}
Returns:
  (message_id, decoded_dict)  — decoded_dict is ready to send as a JSON frame
  (None, None)                — unknown or outbound message ID (skip)
  (0, 0)                      — outbound command IDs (skip silently)
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

TABLE_NAME_MAP = {
    0x0CFF020A: "M1_OutputLC1_0x0CFF020A",
    0x0CFF030A: "M1_OutputSP_0x0CFF030A",
    0x0CFF050A: "M1_Commands_0x0CFF050A",
    0x0CFF060A: "Set_ID_0x0CFF060A",
    0x0CFF070A: "Set_SM_0x0CFF070A",
    0x0CFF080A: "Set_CycleA_0x0CFF080A",
    0x0CFF090A: "Set_CycleB_0x0CFF090A",
    0x0CFF0A0A: "Set_ScaleT_0x0CFF0A0A",
    0x0CFF0B0A: "Set_ScaleF_0x0CFF0B0A",
    0x0CFF0D14: "M2_Data1_0x0CFF0D14",
    0x0CFF0E14: "M2_Data2_0x0CFF0E14",
    0x0CFF000A: "FloPSI_0x0CFF000A",
    0x0CFF010A: "TempDigSet_0x0CFF010A",
    0x0CFF040A: "M1Timers_0x0CFF040A",
    0x0CFF0C0A: "Scaled_M2_Data_0x0CFF0C0A",
    0x0CFF110A: "M1Ports_0x0CFF110A",
    0x0CFF0F14: "M2Ports_0x0CFF0F14",
}

# Outbound command IDs — sent by us, not logged
OUTBOUND_IDS = {0x0CFF101E, 0x0CFF121E, 0x0CFF131E, 0x0CFF141E, 0x0CFF151E, 0x0CFF161E, 0x0CFF171E}

BUBBLE_MAP = {
    131: "B31: WO Entry",
    103: "B3: SP Ramp Down",
    132: "B32: Write To Mem",
    102: "B2: SP> WaitForRPM",
    101: "B1: Wait for Start",
    105: "B5: Wait 30 Seconds",
    110: "B10: Wait For Seq Order",
    104: "B4: LC Ramp Down",
    109: "B9: TP Ramp Down",
    157: "B57: TP Ramp Up",
    159: "B59: Delay",
    116: "B16: LC Ramp",
    134: "B34: TP Ramp Up",
    111: "B11: Set Cycle Params",
    130: "B30: Tp Ramp Up",
    135: "B35: Pause Timer",
    160: "B60: Tp Ramp Down",
    156: "B56: Check If In Test",
    152: "B52: TP Ramp Down",
    153: "B53: Switch -n- 6s",
    201: "B01: Wait For Start",
    202: "B02: SP> WaitForRPM",
    203: "B03: SP Ramp Down",
    205: "Set Pump Parameters",
}


def decode_message(message: dict) -> tuple:
    data = message["data"]
    message_id = message.get("arbitration")
    timestamp = datetime.fromtimestamp(message["timestamp"]).isoformat()

    if message_id is None:
        logger.error("Message has no arbitration_id: %s", message)
        return None, None

    if message_id in OUTBOUND_IDS:
        return 0, 0  # Silently skip our own outbound frames

    table_name = TABLE_NAME_MAP.get(message_id)
    if table_name is None:
        logger.debug("Unknown CAN ID: %s", hex(message_id))
        return message_id, {}

    base = {"table_name": table_name, "timestamp": timestamp, "message_id": message_id}

    if message_id == 0x0CFF000A:
        return message_id, {**base,
            "signalDispP1": data[0] | (data[1] << 8),
            "signalDispF2": data[2] | (data[3] << 8),
            "signalDispS1": data[4] | (data[5] << 8),
            "signalDispP5": data[6] | (data[7] << 8),
        }

    if message_id == 0x0CFF010A:
        return message_id, {**base,
            "signalT1":              data[0] | (data[1] << 8),
            "signalT3":              data[2] | (data[3] << 8),
            "signalStart":           (data[4] & 0x01),
            "signalStop_sw":         (data[4] & 0x02) >> 1,
            "signalPB4":             (data[4] & 0x04) >> 2,
            "signaleStop_sw":        (data[4] & 0x08) >> 3,
            "signalTP_FWD":          (data[4] & 0x10) >> 4,
            "signalTP_REV":          (data[4] & 0x20) >> 5,
            "signalLED":             (data[4] & 0x40) >> 6,
            "signalLogging":         (data[4] & 0x80) >> 7,
            "signalDispTP":          data[5] | (data[6] << 8),
            "signalOut_TP_Enabled":  (data[7] & 0x01),
            "signalOut_TP_Reved":    (data[7] & 0x02) >> 1,
            "signalStarted":         (data[7] & 0x04) >> 2,
            "signalStopped":         (data[7] & 0x08) >> 3,
            "signalE_Stopped":       (data[7] & 0x10) >> 4,
        }

    if message_id == 0x0CFF020A:
        return message_id, {**base,
            "signalLC1":          data[0] | (data[1] << 8),
            "signalLC1_Setpoint": data[2] | (data[3] << 8),
            "signalLC1_Feedback": data[4] | (data[5] << 8),
            "signalLC1_Enable":   (data[6] & 0x01),
            "signalLC1_State":    (data[6] & 0x04) >> 2,
            "signalLC1_Regulate": (data[6] & 0x08) >> 4,
        }

    if message_id == 0x0CFF030A:
        return message_id, {**base,
            "signalSP":         data[0] | (data[1] << 8),
            "signalSPSetpoint": data[2] | (data[3] << 8),
            "signalSPFeedback": data[4] | (data[5] << 8),
            "signalSP_enable":  (data[6] & 0x01),
            "signalSP_Regulate":(data[6] & 0x02) >> 1,
            "signalSP_Rev":     (data[6] & 0x04) >> 2,
        }

    if message_id == 0x0CFF040A:
        bubble_value = data[6] | (data[7] << 8)
        return message_id, {**base,
            "signalDelay":      data[0] | (data[1] << 8),
            "signalCycle":      data[2] | (data[3] << 8),
            "signalCycleTimer": data[4] | (data[5] << 8),
            "signalBubble":     bubble_value,
            "signalBubbleStr":  BUBBLE_MAP.get(bubble_value, "Unknown"),
        }

    if message_id == 0x0CFF050A:
        return message_id, {**base,
            "signalSol_A":       (data[0] & 0x01),
            "signalSol_B":       (data[0] & 0x02) >> 1,
            "signalTP9A_Enable": (data[0] & 0x04) >> 2,
            "signalTP9A_Dir":    (data[0] & 0x08) >> 3,
            "signalStop_LED":    (data[0] & 0x10) >> 4,
            "signalPolarity":    (data[0] & 0x20) >> 5,
            "signalTP9A_Cmd":    data[1] | (data[2] << 8),
            "signal_Scaled_F3":  data[3] | (data[4] << 8),
            "signal_Save_Logs":  (data[5] & 0x01),
        }

    if message_id == 0x0CFF060A:
        return message_id, {**base,
            "signalEECustomerID1":   data[0] | (data[1] << 8),
            "signalEECustomerID2":   data[2] | (data[3] << 8),
            "signalEE_LC1_Rate":     data[4] | (data[5] << 8),
            "signalEE_MaxCycles":    data[6],
            "signalEE_EE_SM_Dir":    (data[7] & 0x01),
            "signalEE_EE_TP_Reverse":(data[7] & 0x02) >> 1,
        }

    if message_id == 0x0CFF070A:
        return message_id, {**base,
            "signalEE_SM_RPM":       data[0] | (data[1] << 8),
            "signalEE_SM_Rate":      data[2] | (data[3] << 8),
            "signalEE_SM_Timer":     data[4] | (data[5] << 8),
            "signalEECycleDelay":    data[6] | (data[7] << 8),
        }

    if message_id == 0x0CFF080A:
        return message_id, {**base,
            "signalEECycleTime1": data[0],
            "signalEECycleTime2": data[1],
            "signalEECycleTime3": data[2],
            "signalEECycleTime4": data[3],
            "signalEECycleTime5": data[4],
            "signalEECyclePSI1":  data[5] | (data[6] << 8),
        }

    if message_id == 0x0CFF090A:
        return message_id, {**base,
            "signalEECyclePSI2": data[0] | (data[1] << 8),
            "signalEECyclePSI3": data[2] | (data[3] << 8),
            "signalEECyclePSI4": data[4] | (data[5] << 8),
            "signalEECyclePSI5": data[6] | (data[7] << 8),
        }

    if message_id == 0x0CFF0A0A:
        return message_id, {**base,
            "signalEE_T1_Scale": data[0] | (data[1] << 8),
            "signalEE_T3_Scale": data[2] | (data[3] << 8),
            "signalEE_F1_Scale": data[4] | (data[5] << 8),
            "signalEE_F2_Scale": data[6] | (data[7] << 8),
        }

    if message_id == 0x0CFF0B0A:
        return message_id, {**base,
            "signalEE_F3_Scale": data[0] | (data[1] << 8),
            "signalEE_P1_Scale": data[2] | (data[3] << 8),
            "signalEE_P5_Scale": data[4] | (data[5] << 8),
            "signalEE_P4_Scale": data[6] | (data[7] << 8),
        }

    if message_id == 0x0CFF0C0A:
        return message_id, {**base,
            "signal_Scaled_P2": data[0] | (data[1] << 8),
            "signal_Scaled_P3": data[2] | (data[3] << 8),
            "signal_Scaled_P4": data[4] | (data[5] << 8),
            "signal_Scaled_F1": data[6] | (data[7] << 8),
        }

    if message_id == 0x0CFF0D14:
        return message_id, {**base,
            "SignalF1": data[0] | (data[1] << 8),
            "SignalP2": data[2] | (data[3] << 8),
            "SignalP3": data[4] | (data[5] << 8),
            "SignalP4": data[6] | (data[7] << 8),
        }

    if message_id == 0x0CFF0E14:
        return message_id, {**base,
            "signalM2_F3":         data[0] | (data[1] << 8),
            "signalM2_POT":        data[2] | (data[3] << 8),
            "signalM2_Sol_A":      (data[4] & 0x01),
            "signalM2_Sol_B":      (data[4] & 0x02) >> 1,
            "signalM2_TP9A_enable":(data[4] & 0x04) >> 2,
            "signalM2_TP9A_Dir":   (data[4] & 0x08) >> 3,
            "signalM2_Stop_LED":   (data[4] & 0x10) >> 4,
            "signalM2_Polarity":   (data[4] & 0x20) >> 5,
            "signalM2_TP9A":       data[5] | (data[6] << 8),
        }

    if message_id == 0x0CFF110A:
        return message_id, {**base,
            "signalSP_Open":           (data[0] & 0x01),
            "signalSP_Short":          (data[0] & 0x02) >> 1,
            "signalSP_Enable_Open":    (data[0] & 0x04) >> 2,
            "signalSP_Enable_Short":   (data[0] & 0x08) >> 3,
            "signalSP_REV_Open":       (data[0] & 0x10) >> 4,
            "signalSP_REV_Short":      (data[0] & 0x20) >> 5,
            "signalTP_Open":           (data[1] & 0x01),
            "signalTP_Short":          (data[1] & 0x02) >> 1,
            "signalTP_ENABLE_Open":    (data[1] & 0x04) >> 2,
            "signalTP_ENABLE_Short":   (data[1] & 0x08) >> 3,
            "signalTP_REV_Open":       (data[1] & 0x10) >> 4,
            "signalTP_REV_Short":      (data[1] & 0x20) >> 5,
            "signalLC1_Open":          (data[2] & 0x01),
            "signalLC1_Short":         (data[2] & 0x02) >> 1,
            "signalLC1_PWR_Open":      (data[2] & 0x04) >> 2,
            "signalLC1_PWR_Short":     (data[2] & 0x08) >> 3,
            "signalLED_Open":          (data[2] & 0x10) >> 4,
            "signalLED_Short":         (data[2] & 0x20) >> 5,
            "signalM1_Blink":          (data[2] & 0x40) >> 6,
        }

    if message_id == 0x0CFF0F14:
        return message_id, {**base,
            "signalPolarity_Open":    (data[0] & 0x01),
            "signalPolarity_Short":   (data[0] & 0x02) >> 1,
            "signalStop_Lamp_Open":   (data[0] & 0x04) >> 2,
            "signalStop_Lamp_Short":  (data[0] & 0x08) >> 3,
            "signalSOL_A_Open":       (data[0] & 0x10) >> 4,
            "signalSOL_A_Short":      (data[0] & 0x20) >> 5,
            "signalSOL_B_Open":       (data[0] & 0x40) >> 6,
            "signalSOL_B_Short":      (data[0] & 0x80) >> 7,
            "signalTP9A_Open":        (data[1] & 0x01),
            "signalTP9A_Short":       (data[1] & 0x02) >> 1,
            "signalTP9A_FWD_Open":    (data[1] & 0x04) >> 2,
            "signalTP9A_FWD_Short":   (data[1] & 0x08) >> 3,
            "signalTP9A_REV_Open":    (data[1] & 0x10) >> 4,
            "signalTP9A_REV_Short":   (data[1] & 0x20) >> 5,
            "signalM2_Blink":         (data[2] & 0x40) >> 6,
            "signalSupplyVoltage":    data[2] | (data[3] << 8),
        }

    return message_id, {}


def decoded_to_live_frame(decoded: dict) -> dict | None:
    """
    Converts a decoded CAN message into a flat live-data frame suitable for
    broadcasting to frontend clients. Only messages that contribute to the
    live display are mapped here.
    """
    mid = decoded.get("message_id")

    if mid == 0x0CFF000A:
        return {
            "p1": decoded["signalDispP1"],
            "f2": decoded["signalDispF2"],
            "s1": decoded["signalDispS1"],
            "p5": decoded["signalDispP5"],
        }
    if mid == 0x0CFF010A:
        return {
            "t1":       decoded["signalT1"],
            "t3":       decoded["signalT3"],
            "trending": decoded["signalLogging"],
            "tp":       decoded["signalDispTP"],
            "pb4":      decoded["signalPB4"],
            "tp_reved": decoded["signalOut_TP_Reved"],
        }
    if mid == 0x0CFF020A:
        return {
            "lcSetpoint": decoded["signalLC1_Setpoint"],
            "lcRegulate": decoded["signalLC1_Regulate"],
        }
    if mid == 0x0CFF030A:
        return {"sp": decoded["signalSP"]}
    if mid == 0x0CFF040A:
        return {
            "delay":      decoded["signalDelay"],
            "cycle":      decoded["signalCycle"],
            "cycleTimer": decoded["signalCycleTimer"],
            "step":       decoded["signalBubbleStr"],
        }
    if mid == 0x0CFF050A:
        return {"f3": decoded["signal_Scaled_F3"]}
    if mid == 0x0CFF0C0A:
        return {
            "p2": decoded["signal_Scaled_P2"],
            "p4": decoded["signal_Scaled_P4"],
            "f1": decoded["signal_Scaled_F1"],
        }
    if mid == 0x0CFF0D14:
        return {"p3": decoded["SignalP3"]}
    if mid == 0x0CFF0E14:
        return {"m2_tp9a_dir": decoded["signalM2_TP9A_Dir"]}

    return None  # Message doesn't contribute to the live display
