import logging
import wexpect
import time
import can
from datetime import datetime

from databaseManipulation import write_to_db

# Configure logging 
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')


def decode_message(message):
    

    data = message['data']
    message_id = message.get('arbitration', None)
    timestamp = datetime.fromtimestamp(message['timestamp']).isoformat()
    
    # Check if message_id is None processing further
    if message_id is None:
        logging.error(f"Message has no arbitration_id. Message: {message}")
        return None, None

    table_name_mapping = {
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
        0x0CFF0F14: "M2Ports_0x0CFF0F14"
    }

    table_name = table_name_mapping.get(message_id, None)
    if table_name is None:
        logging.warning(f"No table found for CAN ID: {hex(message_id)}")
        return None, None

    if message_id == 0x0CFF000A:
        decoded_message = {
            'table_name': table_name,
            'timestamp': timestamp,
            'message_id': message_id,
            'signalDispP1': data[0] | (data[1] << 8),
            'signalDispF2': data[2] | (data[3] << 8),
            'signalDispS1': data[4] | (data[5] << 8),
            'signalDispP5': data[6] | (data[7] << 8)
        }
        return message_id, decoded_message

    elif message_id == 0x0CFF010A:
        decoded_message = {
            'table_name': table_name,
            'timestamp': timestamp,
            'message_id': message_id,
            'signalT1': data[0] | (data[1] << 8),
            'signalT3': data[2] | (data[3] << 8),
            'signalStart': (data[4] & 0x01),
            'signalStop_sw': (data[4] & 0x02) >> 1,
            'signalPB4': (data[4] & 0x04) >> 2,
            'signaleStop_sw': (data[4] & 0x08) >> 3,
            'signalTP_FWD': (data[4] & 0x10) >> 4,
            'signalTP_REV': (data[4] & 0x20) >> 5,
            'signalLED': (data[4] & 0x40) >> 6,
            'signalLogging': (data[4] & 0x80) >> 7,
            'signalDispTP': data[5] | (data[6] << 8),
            'signalOut_TP_Enabled': (data[7] & 0x01),
            'signalOut_TP_Reved': (data[7] & 0x02) >> 1,
            'signalStarted': (data[7] & 0x04) >> 2,
            'signalStopped': (data[7] & 0x08) >> 3,
            'signalE_Stopped': (data[7] & 0x10) >> 4
        }
        return message_id, decoded_message

    elif message_id == 0x0CFF020A:
        decoded_message = {
            'table_name': table_name,
            'timestamp': timestamp,
            'message_id': message_id,
            'signalLC1': data[0] | (data[1] << 8),
            'signalLC1_Setpoint': data[2] | (data[3] << 8),
            'signalLC1_Feedback': data[4] | (data[5] << 8),
            'signalLC1_Enable': (data[6] & 0x01),
            'signalLC1_State': (data[6] & 0x04) >> 2,
            'signalLC1_Regulate': (data[6] & 0x08)>>4
        }
        return message_id, decoded_message

    elif message_id == 0x0CFF030A:
        decoded_message = {
            'table_name': table_name,
            'timestamp': timestamp,
            'message_id': message_id,
            'signalSP': data[0] | (data[1] << 8),
            'signalSPSetpoint': data[2] | (data[3] << 8),
            'signalSPFeedback': data[4] | (data[5] << 8),
            'signalSP_enable': (data[6] & 0x01),
            'signalSP_Regulate': (data[6] & 0x02) >> 1,
            'signalSP_Rev': (data[6] & 0x04) >> 2
        }
        return message_id, decoded_message

    elif message_id == 0x0CFF040A:
        decoded_message = {
            'table_name': table_name,
            'timestamp': timestamp,
            'message_id': message_id,
            'signalDelay': data[0] | (data[1] << 8),
            'signalCycle': data[2] | (data[3] << 8),
            'signalCycleTimer': data[4] | (data[5] << 8),
            'signalBubble': data[6] | (data[7] << 8)
        }
        # if state is new set state to old 
        # print statements for signalBubble 
        # global statement for new and bubble match, backup, some variable to say that we are finished with a test and we are backing things up now
        # if 101 and new set new to false and save csv, database, and excel sheet, and then clear those items
        # Prepare to start logging again
        # once not 101, new to true
        # once 101 is true and new is true, 
        
        return message_id, decoded_message

    elif message_id == 0x0CFF050A:
        decoded_message = {
            'table_name': table_name,
            'timestamp': timestamp,
            'message_id': message_id,
            'signalSol_A': (data[0] & 0x01),
            'signalSol_B': (data[0] & 0x02) >> 1,
            'signalTP9A_Enable': (data[0] & 0x02) >> 2,
            'signalTP9A_Dir': (data[0] & 0x03) >> 3,
            'signalStop_LED': (data[0] & 0x01) >> 4,
            'signalPolarity': (data[0] & 0x01) >> 5,
            'signalTP9A_Cmd': data[1] | (data[2] << 8),
            'signal_Scaled_F3': data[3] | (data[4] << 8),
            'signal_Save_Logs': (data[5] & 0x01)
        }
        return message_id, decoded_message

    elif message_id == 0x0CFF060A:
        decoded_message = {
            'table_name': table_name,
            'timestamp': timestamp,
            'message_id': message_id,
            'signalEECustomerID1': data[0] | (data[1] << 8),
            'signalEECustomerID2': data[2] | (data[3] << 8),
            'signalEE_LC1_Rate': data[4] | (data[5] << 8),
            'signalEE_MaxCycles': data[6],
            'signalEE_EE_SM_Dir': (data[7] & 0x01),
            'signalEE_EE_TP_Reverse': (data[7] & 0x02) >> 1
        }
        return message_id, decoded_message

    elif message_id == 0x0CFF070A:
        decoded_message = {
            'table_name': table_name,
            'timestamp': timestamp,
            'message_id': message_id,
            'signalEE_SM_RPM': data[0] | (data[1] << 8),
            'signalEE_SM_Rate': data[2] | (data[3] << 8),
            'signalEE_SM_Timer': data[3] | (data[4] << 8),
            'signalEECycleDelay': data[4] | (data[5] << 8),
            'signalEE_TP_Max_Percent': data[6]
        }
        return message_id, decoded_message

    elif message_id == 0x0CFF080A:
        decoded_message = {
            'table_name': table_name,
            'timestamp': timestamp,
            'message_id': message_id,
            'signalEECycleTime1': data[0],
            'signalEECycleTime2': data[1],
            'signalEECycleTime3': data[2],
            'signalEECycleTime4': data[3],
            'signalEECycleTime5': data[4],
            'signalEECyclePSI1': data[5] | (data[6] << 8)
        }
        return message_id, decoded_message

    elif message_id == 0x0CFF090A:
        decoded_message = {
            'table_name': table_name,
            'timestamp': timestamp,
            'message_id': message_id,
            'signalEECyclePSI2': data[0] | (data[1] << 8),
            'signalEECyclePSI3': data[2] | (data[3] << 8),
            'signalEECyclePSI4': data[4] | (data[5] << 8),
            'signalEECyclePSI5': data[6] | (data[7] << 8)
        }
        return message_id, decoded_message

    elif message_id == 0x0CFF0A0A:
        decoded_message = {
            'table_name': table_name,
            'timestamp': timestamp,
            'message_id': message_id,
            'signalEE_T1_Scale': data[0] | (data[1] << 8),
            'signalEE_T3_Scale': data[2] | (data[3] << 8),
            'signalEE_F1_Scale': data[4] | (data[5] << 8),
            'signalEE_F2_Scale': data[6] | (data[7] << 8)
        }
        return message_id, decoded_message

    elif message_id == 0x0CFF0B0A:
        decoded_message = {
            'table_name': table_name,
            'timestamp': timestamp,
            'message_id': message_id,
            'signalEE_F3_Scale': data[0] | (data[1] << 8),
            'signalEE_P1_Scale': data[2] | (data[3] << 8),
            'signalEE_P5_Scale': data[4] | (data[5] << 8),
            'signalEE_P4_Scale': data[6] | (data[7] << 8)
        }
        return message_id, decoded_message

    elif message_id == 0x0CFF0C0A:
        decoded_message = {
            'table_name': table_name,
            'timestamp': timestamp,
            'message_id': message_id,
            'signal_Scaled_P2': data[0] | (data[1] << 8),
            'signal_Scaled_P3': data[2] | (data[3] << 8),
            'signal_Scaled_P4': data[4] | (data[5] << 8),
            'signal_Scaled_F1': data[6] | (data[7] << 8)
        }
        return message_id, decoded_message

    elif message_id == 0x0CFF0D14:
        decoded_message = {
            'table_name': table_name,
            'timestamp': timestamp,
            'message_id': message_id,
            'SignalF1': data[0] | (data[1] << 8),
            'SignalP2': data[2] | (data[3] << 8),
            'SignalP3': data[4] | (data[5] << 8),
            'SignalP4': data[6] | (data[7] << 8)
        }
        return message_id, decoded_message

    elif message_id == 0x0CFF0E14:
        decoded_message = {
            'table_name': table_name,
            'timestamp': timestamp,
            'message_id': message_id,
            'signalM2_F3': data[0] | (data[1] << 8),
            'signalM2_POT': data[2] | (data[3] << 8),
            'signalM2_Sol_A': (data[4] & 0x01),
            'signalM2_Sol_B': (data[4] & 0x02) >> 1,
            'signalM2_TP9A_enable': (data[4] & 0x04) >> 2,
            'signalM2_TP9A_Dir': (data[4] & 0x08) >> 3,
            'signalM2_Stop_LED': (data[4] & 0x10) >> 4,
            'signalM2_Polarity': (data[4] & 0x20) >> 5,
            'signalM2_TP9A': data[5] | (data[6] << 8)
        }
        return message_id, decoded_message
        
    elif message_id == 0x0CFF110A:
        decoded_message = {
            'table_name': table_name,
            'timestamp': timestamp,
            'message_id': message_id,
            'signalSP_Open': (data[0] & 0x01),
            'signalSP_Short': (data[0] & 0x02) >> 1,
            'signalSP_Enable_Open': (data[0] & 0x04) >> 2,
            'signalSP_Enable_Short': (data[0] & 0x08) >> 3,
            'signalSP_REV_Open': (data[0] & 0x10) >> 4,
            'signalSP_REV_Short': (data[0] & 0x20) >> 5,
            'signalTP_Open': (data[1] & 0x01),
            'signalTP_Short': (data[1] & 0x02) >> 1,
            'signalTP_ENABLE_Open': (data[1] & 0x04) >> 2,
            'signalTP_ENABLE_Short': (data[1] & 0x08) >> 3,
            'signalTP_REV_Open': (data[1] & 0x10) >> 4,
            'signalTP_REV_Short': (data[1] & 0x20) >> 5,
            'signalLC1_Open': (data[2] & 0x01),
            'signalLC1_Short': (data[2] & 0x02) >> 1,
            'signalLC1_PWR_Open': (data[2] & 0x04) >> 2,
            'signalLC1_PWR_Short': (data[2] & 0x08) >> 3,
            'signalLED_Open': (data[2] & 0x10) >> 4,
            'signalLED_Short': (data[2] & 0x20) >> 5,
            'signalM1_Blink': (data[2] &  0x40) >> 6
        }
        return message_id, decoded_message

    elif message_id == 0x0CFF0F14:
        decoded_message = {
            'table_name': table_name,
            'timestamp': timestamp,
            'message_id': message_id, 
            'signalPolarity_Open': (data[0] & 0x01),
            'signalPolarity_Short': (data[0] & 0x02) >> 1,
            'signalStop_Lamp_Open': (data[0] & 0x04) >> 2,
            'signalStop_Lamp_Short': (data[0] & 0x08) >> 3,
            'signalSOL_A_Open': (data[0] & 0x10) >> 4,
            'signalSOL_A_Short': (data[0] & 0x20) >> 5,
            'signalSOL_B_Open': (data[0] & 0x40) >> 6,
            'signalSOL_B_Short': (data[0] & 0x80) >> 7,
            'signalTP9A_Open': (data[1] & 0x01), 
            'signalTP9A_Short': (data[1] & 0x02) >> 1,
            'signalTP9A_FWD_Open': (data[1] & 0x04) >> 2,
            'signalTP9A_FWD_Short': (data[1] & 0x08) >> 3,
            'signalTP9A_REV_Open': (data[1] & 0x10) >> 4,
            'signalTP9A_REV_Short': (data[1] & 0x20) >> 5,
            'signalM2_Blink': (data[2] & 0x40) >> 6,
            'signalSupplyVoltage': (data[2] | (data[3] << 8))
        }
        return message_id, decoded_message
    # these are the messages that we are sending. We don't need to log these messages. They are either settings, or commands. We light decide to record 0x0CFF101E which has commands, but that will need to be a conversation.
    elif  ((message_id == 0x0CFF101E) or (message_id == 0x0CFF121E) or (message_id == 0x0CFF131E) or (message_id == 0x0CFF141E) or  (message_id == 0x0CFF151E) or (message_id ==  0x0CFF161E) or  (message_id ==  0x0CFF171E)):
        return 0, 0
    else:
        return message_id, {}
    
    
def process_can_data():
    remote_command = 'ssh devteam@192.168.1.90 "candump can0"'
    
    child = wexpect.spawn(remote_command)
    
    try:
        child.expect('password:')
        child.sendline('dponice')

        while True:
            line = child.readline().strip()
            if not line:
                continue

            try:
                # Split the line into components
                parts = line.split()
                
                # Check if the line has the expected structure
                if len(parts) < 5:
                    logging.error(f"Error processing line {line}, not enough parts")
                    continue

                can_id_str = parts[1]  # The CAN ID is the second part
                can_data = parts[3:]  # The actual data bytes start from the fourth part
                
                # Convert the CAN ID to an integer
                can_id = int(can_id_str, 16)
                
                # Convert the data parts into integers
                data = [int(byte, 16) for byte in can_data]
                
                # Use the current time as the timestamp
                timestamp = time.time()
                
                # Mock a message object similar to what decode_message expects
                message = {
                    "arbitration": can_id,
                    "data": data,
                    "timestamp": timestamp
                }
                
                # Decode the message
                message_id, decoded_message = decode_message(message)

                if decoded_message:
                    write_to_db(decoded_message['table_name'], decoded_message)
                else:
                    logging.warning(f"Unknown CAN message ID: {message_id}")
                    
            except ValueError as e:
                logging.error(f"Error processing line: {line}, {e}")
            except Exception as e:
                logging.exception("Unexpected error occurred")
    
    except wexpect.EOF:
        logging.error("SSH session ended unexpectedly.")
    except wexpect.TIMEOUT:
        logging.error("SSH session timed out.")
    finally:
        child.close()

