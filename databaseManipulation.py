import sqlite3
import logging
import os
import pandas as pd
from datetime import datetime
import csv
import time
import dotenv
import shutil

dotenv.load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')

# *RASPBERRY PI* Make sure to adjust the base_path to point at the env file or to the path in the pi
base_path2 = r'C:\Users\tsmith\Coding\WebInterfacePython'
base_path = os.getenv('csv_path')
network_base_path = os.getenv('NETWORK_BASE_PATH')
dvc_csv_path = os.path.join(base_path, 'dvc_values.csv')
bucket_db = os.path.join(base_path, 'bucket.db')
settings_db = os.path.join(base_path, 'settings.db')
can_data_local_db = os.path.join(base_path, 'can_data_local.db')



def initialize_databases():
    # Ensure the base directory exists
    if not os.path.exists(base_path):
        os.makedirs(base_path)

    

    # Initialize settings.db
    conn = sqlite3.connect(settings_db)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS EEMemoryValues (
        id INTEGER PRIMARY KEY,
        customerid1 INTEGER,
        customerid2 INTEGER,
        SM_DIR INTEGER,
        SM_rpm INTEGER,
        SM_rate INTEGER,
        SM_timer INTEGER,
        LC1_rate INTEGER,
        MaxCycles INTEGER,
        CycleTime1 INTEGER,
        CyclePSI1 INTEGER,
        CycleTime2 INTEGER,
        CyclePSI2 INTEGER,
        CycleTime3 INTEGER,
        CyclePSI3 INTEGER,
        CycleTime4 INTEGER,
        CyclePSI4 INTEGER,
        CycleTime5 INTEGER,
        CyclePSI5 INTEGER,
        CycleDelay INTEGER,
        t1scale INTEGER,
        t3scale INTEGER,
        f1scale INTEGER,
        f2scale INTEGER,
        f3scale INTEGER,
        TP_Reverse INTEGER,
        TP_Max_Percent INTEGER,
        P1Scale INTEGER,
        P5Scale INTEGER,
        P4Scale INTEGER
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS AppSettings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        setting_name TEXT UNIQUE,
        setting_value TEXT
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Commands (
        id INTEGER PRIMARY KEY,
        start INTEGER,
        stop INTEGER,
        estop INTEGER
        saveSettings INTEGER
    )
    ''')
    
    conn.commit()
    conn.close()
    
    # Initialize can_data_local.db
    conn = sqlite3.connect(can_data_local_db)
    cursor = conn.cursor()

    #ursor Create tables if they don't exist
    cursor.execute('''CREATE TABLE IF NOT EXISTS FloPSI_0x0CFF000A (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            message_id INTEGER,
            signalDispP1 INTEGER,
            signalDispF2 REAL,
            signalDispS1 INTEGER,
            signalDispP5 INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS TempDigSet_0x0CFF010A (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            message_id INTEGER,
            signalT1 INTEGER,
            signalT3 INTEGER,
            signalStart INTEGER,
            signalStop_sw INTEGER,
            signalPB4 INTEGER,
            signaleStop_sw INTEGER,
            signalTP_FWD INTEGER,
            signalTP_REV INTEGER,
            signalLED INTEGER,
            signalLogging INTEGER,
            signalDispTP INTEGER,
            signalOut_TP_Enabled INTEGER,
            signalOut_TP_Reved INTEGER,
            signalStarted INTEGER,
            signalStopped INTEGER,
            signalE_Stopped INTEGER)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS M1_OutputLC1_0x0CFF020A (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            message_id INTEGER,
            signalLC1 INTEGER,
            signalLC1_Setpoint INTEGER,
            signalLC1_Feedback INTEGER,
            signalLC1_Enable INTEGER,
            signalLC1_State INTEGER,
            signalLC1_Regulate INTEGER)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS M1_OutputSP_0x0CFF030A (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            message_id INTEGER,
            signalSP INTEGER,
            signalSPSetpoint INTEGER,
            signalSPFeedback INTEGER,
            signalSP_enable INTEGER,
            signalSP_Regulate INTEGER,
            signalSP_Rev INTEGER)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS M1Timers_0x0CFF040A (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            message_id INTEGER,
            signalDelay INTEGER,
            signalCycle INTEGER,
            signalCycleTimer INTEGER,
            signalBubble INTEGER)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS M1_Commands_0x0CFF050A (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            message_id INTEGER,
            signalSol_A INTEGER,
            signalSol_B INTEGER,
            signalTP9A_Enable INTEGER,
            signalTP9A_Dir INTEGER,
            signalStop_LED INTEGER,
            signalPolarity INTEGER,
            signalTP9A_Cmd INTEGER,
            signal_Scaled_F3 INTEGER,
            signal_Save_Logs INTEGER)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS Set_ID_0x0CFF060A (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            message_id INTEGER,
            signalEECustomerID1 INTEGER,
            signalEECustomerID2 INTEGER,
            signalEE_LC1_Rate INTEGER,
            signalEE_MaxCycles INTEGER,
            signalEE_EE_SM_Dir INTEGER,
            signalEE_EE_TP_Reverse INTEGER)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS Set_SM_0x0CFF070A (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            message_id INTEGER,
            signalEE_SM_RPM INTEGER,
            signalEE_SM_Rate INTEGER,
            signalEE_SM_Timer INTEGER,
            signalEECycleDelay INTEGER,
            signalEE_TP_Max_Percent INTEGER)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS Set_CycleA_0x0CFF080A (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            message_id INTEGER,
            signalEECycleTime1 INTEGER,
            signalEECycleTime2 INTEGER,
            signalEECycleTime3 INTEGER,
            signalEECycleTime4 INTEGER,
            signalEECycleTime5 INTEGER,
            signalEECyclePSI1 INTEGER)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS Set_CycleB_0x0CFF090A (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            message_id INTEGER,
            signalEECyclePSI2 INTEGER,
            signalEECyclePSI3 INTEGER,
            signalEECyclePSI4 INTEGER,
            signalEECyclePSI5 INTEGER)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS Set_ScaleT_0x0CFF0A0A (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            message_id INTEGER,
            signalEE_T1_Scale INTEGER,
            signalEE_T3_Scale INTEGER,
            signalEE_F1_Scale INTEGER,
            signalEE_F2_Scale INTEGER)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS Set_ScaleF_0x0CFF0B0A (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            message_id INTEGER,
            signalEE_F3_Scale INTEGER,
            signalEE_P1_Scale INTEGER,
            signalEE_P5_Scale INTEGER,
            signalEE_P4_Scale INTEGER)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS Scaled_M2_Data_0x0CFF0C0A (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            message_id INTEGER,
            signal_Scaled_P2 INTEGER,
            signal_Scaled_P3 INTEGER,
            signal_Scaled_P4 INTEGER,
            signal_Scaled_F1 INTEGER)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS M2_Data1_0x0CFF0D14 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            message_id INTEGER,
            SignalF1 INTEGER,
            SignalP2 INTEGER,
            SignalP3 INTEGER,
            SignalP4 INTEGER)''')

    
    cursor.execute('''CREATE TABLE IF NOT EXISTS M2_Data2_0x0CFF0E14 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            message_id INTEGER,
            signalM2_F3 INTEGER,
            signalM2_POT INTEGER,
            signalM2_Sol_A INTEGER,
            signalM2_Sol_B INTEGER,
            signalM2_TP9A_enable INTEGER,
            signalM2_TP9A_Dir INTEGER,
            signalM2_Stop_LED INTEGER,
            signalM2_Polarity INTEGER,
            signalM2_TP9A INTEGER)''')

    # Add the new tables
    cursor.execute('''CREATE TABLE IF NOT EXISTS M1Ports_0x0CFF110A (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            message_id INTEGER,
            signalSP_Open INTEGER,
            signalSP_Short INTEGER,
            signalSP_ENABLE_Open INTEGER,
            signalSP_Enable_Short INTEGER,
            signalSP_REV_Open INTEGER,
            signalSP_REV_Short INTEGER,
            signalTP_Open INTEGER,
            signalTP_Short INTEGER,
            signalTP_ENABLE_Open INTEGER,
            signalTP_ENABLE_Short INTEGER,
            signalTP_REV_Open INTEGER,
            signalTP_REV_Short INTEGER,
            signalLC1_Open INTEGER,
            signalLC1_Short INTEGER,
            signalLC1_PWR_Open INTEGER,
            signalLC1_PWR_Short INTEGER,
            signalLED_Open INTEGER,
            signalLED_Short INTEGER,
            signalM1_Blink INTEGER)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS M2Ports_0x0CFF0F14 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            message_id INTEGER,
            signalPolarity_Open INTEGER,
            signalPolarity_Short INTEGER,
            signalStop_Lamp_Open INTEGER,
            signalStop_Lamp_Short INTEGER,
            signalSOL_A_Open INTEGER,
            signalSOL_A_Short INTEGER,
            signalSOL_B_Open INTEGER,
            signalSOL_B_Short INTEGER,
            signalTP9A_Open INTEGER,
            signalTP9A_Short INTEGER,
            signalTP9A_FWD_Open INTEGER,
            signalTP9A_FWD_Short INTEGER,
            signalTP9A_REV_Open INTEGER,
            signalTP9A_REV_Short INTEGER,
            signalM2_Blink INTEGER,
            signalSupplyVoltage INTEGER)''')
    
    
    conn.commit()
    conn.close()
    
def update_settings(name, value):
    """Insert or update a setting in AppSettings."""
    try:
        conn = sqlite3.connect(settings_db)
        cursor = conn.cursor()
        
        # Print or log the data being inserted/updated
        print(f"Updating settings: {name} = {value}")
        
        cursor.execute('''
        INSERT INTO AppSettings (setting_name, setting_value)
        VALUES (?, ?)
        ON CONFLICT(setting_name) DO UPDATE SET setting_value = excluded.setting_value''', (name, str(value)))
        
        conn.commit()
        logging.info(f"Setting '{name}' updated to '{value}'")
    except sqlite3.Error as e:
        logging.error(f"Database error updating setting '{name}': {e}")
    except Exception as e:
        logging.error(f"Error updating setting '{name}': {e}")
    finally:
        conn.close()
        
def get_setting(name):
    """Retrieve a setting from AppSettings"""
    try:
        conn = sqlite3.connect(settings_db)
        cursor = conn.cursor()
        
        cursor.execute("SELECT setting_value FROM AppSettings WHERE setting_name = ?", (name,))
        result = cursor.fetchone()
        return result[0] if result else None
    except Exception as e:
        logging.error(f"Error fetching setting '{name}': {e}")
        return None
    finally:
        conn.close()
        
def save_header_data(program_name, description, comp_set, input_factor, input_factor_type, serial_number, employee_id, customer_id):
    print("Saving header data:")
    print(f"Program Name: {program_name}, Description: {description}, Comp Set: {comp_set}, Input Factor: {input_factor}, Input Factor Type: {input_factor_type}, Serial Number: {serial_number}, Employee ID: {employee_id}, Customer ID: {customer_id}")
    update_settings('programName', program_name)
    update_settings('description', description)
    update_settings('compSet', comp_set)
    update_settings('inputFactor', input_factor)
    update_settings('inputFactorType', input_factor_type)
    update_settings('serialNumber', serial_number)
    update_settings('employeeId', employee_id)
    update_settings('customerId', customer_id)
    

def fetch_all_settings():
    conn = sqlite3.connect(settings_db)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM AppSettings")
    rows = cursor.fetchall()
    conn.close()
    return rows

print("Current settings in AppSettings table:", fetch_all_settings())

def write_to_db(table_name, decoded_message):
    if not decoded_message:
        logging.error("No decoded message to write to DB")
        return

    conn = sqlite3.connect(can_data_local_db)
    cursor = conn.cursor()

    table_name = f'"{table_name}"'  # Ensure the table name is properly quoted

    # Define all fields to include predefined and custom fields, excluding 'table_name'
    all_fields = ['timestamp', 'message_id'] + [key for key in decoded_message.keys() if key not in ['timestamp', 'message_id', 'table_name']]

    # Ensure values are actual values, not function/method references
    values = [
        decoded_message.get('timestamp', None),
        decoded_message.get('message_id', None),
    ] + [decoded_message.get(field, None) for field in all_fields[2:]]

    placeholders = ', '.join('?' * len(all_fields))
    field_names = ', '.join(all_fields)

    create_table_query = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        message_id INTEGER,
        {', '.join([f"{field} TEXT" for field in all_fields[2:]])}
    )
    """
    try:
        cursor.execute(create_table_query)

        query = f'INSERT INTO {table_name} ({field_names}) VALUES ({placeholders})'
        cursor.execute(query, values)
        conn.commit()
        
        
    except sqlite3.Error as e:
        logging.error(f"SQLite error: {e}")
    except Exception as e:
        logging.exception("Error writing to DB")
    finally:
        conn.close()

def get_input_factor_from_db():
    try:
        conn = sqlite3.connect(settings_db)
        cursor = conn.cursor()
        cursor.execute("SELECT setting_value FROM AppSettings WHERE setting_name = 'inputFactor'")
        input_factor_row = cursor.fetchone()
        input_factor = float(input_factor_row[0]) if input_factor_row else 1.0
        return input_factor
    except Exception as e:
        logging.error(f"Error fetching input factor: {e}")
        return 1.0
    finally:
        conn.close()

    
def get_live_data():
    # Connect to both databases
    conn_data = sqlite3.connect(can_data_local_db)
    conn_settings = sqlite3.connect(settings_db)
    
    try:
        # Fetch inputFactor from AppSettings table
        input_factor = get_input_factor_from_db()
        
        # Fetch inputFactor from AppSettings table
        cursor_settings = conn_settings.cursor()
        cursor_settings.execute("SELECT setting_value FROM AppSettings WHERE setting_name = 'inputFactor'")
        input_factor_row = cursor_settings.fetchone()
        input_factor = float(input_factor_row[0]) if input_factor_row else 1.0
        
        # Fetch data from can_data_local_db
        cursor_data = conn_data.cursor()
    
    
        cursor_data.execute("SELECT * FROM FloPSI_0x0CFF000A ORDER BY timestamp DESC LIMIT 1")
        data_flo_psi = cursor_data.fetchone()
        
        cursor_data.execute("SELECT * FROM M1Timers_0x0CFF040A ORDER BY timestamp DESC LIMIT 1")
        data_timers = cursor_data.fetchone()
        
        cursor_data.execute("SELECT * FROM M1_OutputLC1_0x0CFF020A ORDER BY timestamp DESC LIMIT 1")
        data_lc1 = cursor_data.fetchone()
        
        cursor_data.execute("SELECT * FROM M1_OutputSP_0x0CFF030A ORDER BY timestamp DESC LIMIT 1")
        data_sp = cursor_data.fetchone()
        
        cursor_data.execute("SELECT * FROM TempDigSet_0x0CFF010A ORDER BY timestamp DESC LIMIT 1")
        data_temp = cursor_data.fetchone()
        
        cursor_data.execute("SELECT * FROM M2_Data1_0x0CFF0D14 ORDER BY timestamp DESC LIMIT 1")
        data_m2_1 = cursor_data.fetchone()
        
        cursor_data.execute("SELECT * FROM M2_Data2_0x0CFF0E14 ORDER BY timestamp DESC LIMIT 1")
        data_m2_2 = cursor_data.fetchone()
        
        cursor_data.execute("SELECT * FROM Set_ScaleF_0x0CFF0B0A ORDER BY timestamp DESC LIMIT 1")
        data_scale_f = cursor_data.fetchone()
        
        cursor_data.execute("SELECT * FROM Scaled_M2_Data_0x0CFF0C0A ORDER BY timestamp DESC LIMIT 1")
        data_scaled_m2 = cursor_data.fetchone()
        
        cursor_data.execute("SELECT * FROM M1_Commands_0x0CFF050A ORDER BY timestamp DESC LIMIT 1")
        data_commands = cursor_data.fetchone()
        
    finally:
        # Close both connection
        conn_data.close()
        conn_settings.close()
        
    # define the mapping for signalBubble
    bubble_mapping = {
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
        205: "Set Pump Parameters"
    }
    
    # Map the signalBubble value to its corresponding string
    bubble_value = data_timers[6] if data_timers else 0
    bubble_string = bubble_mapping.get(bubble_value, "Unknown")
    
    return {
        's1': data_flo_psi[5] if data_flo_psi else 0, # signalDispS1
        'sp': data_sp[3] if data_sp else 0, # signalSP
        'tp': data_temp[13] if data_temp else 0, # signalDispTP
        'delay': data_timers[3] if data_timers else 0, # signalDelay
        'trending': data_temp[12] if data_temp else 0, # signalLogging
        'cycle': data_timers[4] if data_timers else 0, # signalCycle
        'cycleTimer': data_timers[5] if data_timers else 0, # signalCycleTimer
        'lcSetpoint': data_lc1[4] if data_lc1 else 0, # signalLC1_SetPoint
        'lcRegulate': data_lc1[7] if data_lc1 else 0, # Assuming regulation logic to be implemented
        'step': bubble_string,
        't1': data_temp[3] if data_temp else 0, # signalT1
        't3': data_temp[4] if data_temp else 0, # signalT3
        'f1': data_scaled_m2[6] if data_scaled_m2 else 0, # signal_Scaled_F1
        'f2': data_flo_psi[4] if data_flo_psi else 0, # signalDispF2
        'f3': data_commands[10] if data_commands else 0, # signalScaled_F3
        'p1': data_flo_psi[3] if data_flo_psi else 0, # signalDispP1
        'p5': data_flo_psi[6] if data_flo_psi else 0, # signalDispP5
        'p2': data_scaled_m2[3] if data_scaled_m2 else 0, # signal_Scaled_P2
        'p3': data_m2_1[5] if data_m2_1 else 0, # signal_Scaled_P3
        'p4': data_scaled_m2[5] if data_scaled_m2 else 0, # signal_Scaled_P4
    }


def log_data_to_csv():
    
    while True:
        conn = sqlite3.connect(can_data_local_db)
        cursor = conn.cursor()
        
        # Check if logging is active
        cursor.execute("SELECT signalLogging FROM TempDigSet_0x0CFF010A ORDER BY id DESC LIMIT 1")
        result = cursor.fetchone()
        
        # Ensure that a result was returned
        if result is None:
            # Handle the case where there is no data
            print("No signalLogging data found in the database.")
            conn.close()
            time.sleep(5)
            continue
        
        signalLogging = result[0]
        
        if signalLogging == 1:
            # Define the columns for the CSV
            columns = ["Date", "Time", "S1", "SP", "TP", "Cycle", "Cycle Timer", "LCSetpoint", "LC Regulate", "Step", "F1", "F2", "F3", "T1", "T3", "P1", "P2", "P3", "P4", "P5"]
            # Define the query to get the data from the database
            query = """
            SELECT 
                date('now'), time('now'),
                (SELECT signalDispS1 FROM FloPSI_0x0CFF000A ORDER BY timestamp DESC LIMIT 1),
                (SELECT signalSP FROM M1_OutputSP_0x0CFF030A ORDER BY timestamp DESC LIMIT 1),
                (SELECT signalDispTP FROM TempDigSet_0x0CFF010A ORDER BY timestamp DESC LIMIT 1),
                (SELECT signalCycle FROM M1Timers_0x0CFF040A ORDER BY timestamp DESC LIMIT 1),
                (SELECT signalCycleTimer FROM M1Timers_0x0CFF040A ORDER BY timestamp DESC LIMIT 1),
                (SELECT signalLC1_Setpoint FROM M1_OutputLC1_0x0CFF020A ORDER BY timestamp DESC LIMIT 1),
                (SELECT signalLC1_Regulate FROM M1_OutputLC1_0x0CFF020A ORDER BY timestamp DESC LIMIT 1),
                (SELECT signalBubble FROM M1Timers_0x0CFF040A ORDER BY timestamp DESC LIMIT 1),
                (SELECT signal_Scaled_F1 FROM Scaled_M2_Data_0x0CFF0C0A ORDER BY timestamp DESC LIMIT 1),
                (SELECT signalDispF2 FROM FloPSI_0x0CFF000A ORDER BY timestamp DESC LIMIT 1),
                (SELECT signal_Scaled_F3 FROM M1_Commands_0x0CFF050A ORDER BY timestamp DESC LIMIT 1),
                (SELECT signalT1 FROM TempDigSet_0x0CFF010A ORDER BY timestamp DESC LIMIT 1),
                (SELECT signalT3 FROM TempDigSet_0x0CFF010A ORDER BY timestamp DESC LIMIT 1),
                (SELECT signalDispP1 FROM FloPSI_0x0CFF000A ORDER BY timestamp DESC LIMIT 1),
                (SELECT signal_Scaled_P2 FROM Scaled_M2_Data_0x0CFF0C0A ORDER BY timestamp DESC LIMIT 1),
                (SELECT SignalP3 FROM M2_Data1_0x0CFF0D14 ORDER BY timestamp DESC LIMIT 1),
                (SELECT signal_Scaled_P4 FROM Scaled_M2_Data_0x0CFF0C0A ORDER BY timestamp DESC LIMIT 1),
                (SELECT signalDispP5 FROM FloPSI_0x0CFF000A ORDER BY timestamp DESC LIMIT 1)
            """
            cursor.execute(query)
            data = cursor.fetchone()
            
            # Ensure that a result was returned
            if data is None:
                print("No data found for logging")
                conn.close()
                time.sleep(5)
                continue
            
            # convert the data to a pandas DateFrame
            df = pd.DataFrame([data], columns=columns)
            
            # Log the data to CSV
            if not os.path.isfile(os.path.join(base_path, 'log_data.csv')):
                with open(os.path.join(base_path, 'log_data.csv'), 'w', newline='') as file:
                    df.to_csv(file, index=False)
            else:
                with open(os.path.join(base_path, 'log_data.csv'), 'a', newline='') as file:
                    
                    df.to_csv(file, mode='a', header=False, index=False)
        
        conn.close()
        time.sleep(5) # Check every 5 seconds
        
        
def get_dvc_values():
    conn = sqlite3.connect('can_data_local.db')
    cursor = conn.cursor()
    
    # fetch values from Set_CycleA_0x0CFF080A
    cursor.execute("SELECT * FROM Set_CycleA_0x0CFF080A ORDER BY id DESC LIMIT 1")
    cycle_a_values = cursor.fetchone()
    
    # fetch values from Set_CycleB_0x0CFF090A
    cursor.execute("SELECT * FROM Set_CycleB_0x0CFF090A ORDER BY id DESC LIMIT 1")
    cycle_b_values = cursor.fetchone()
    
    # fetch values from Set_ID_0x0CFF060A
    cursor.execute("SELECT * FROM Set_ID_0x0CFF060A ORDER BY id DESC LIMIT 1")
    set_id_values = cursor.fetchone()
    
    # fetch values from Set_SM_0x0CFF070A
    cursor.execute("SELECT * FROM Set_SM_0x0CFF070A ORDER BY id DESC LIMIT 1")
    set_sm_values = cursor.fetchone()
    
    # fetch valuees from Set_ScaleF_0x0CFF0B0A
    cursor.execute("SELECT * FROM Set_ScaleF_0x0CFF0B0A ORDER BY id DESC LIMIT 1")
    scale_f_values = cursor.fetchone()
    
    # fetch values from Set_ScaleT_0x0CFF0A0A
    cursor.execute("SELECT * FROM Set_ScaleT_0x0CFF0A0A ORDER BY id DESC LIMIT 1")
    scale_t_values = cursor.fetchone()
    
    conn.close()
    
    # combine all fetched values into a dictionary
    return {
        'CycleTime1': cycle_a_values[3] if cycle_a_values and len(cycle_a_values) > 3 else None,
        'CycleTime2': cycle_a_values[4] if cycle_a_values and len(cycle_a_values) > 4 else None,
        'CycleTime3': cycle_a_values[5] if cycle_a_values and len(cycle_a_values) > 5 else None,
        'CycleTime4': cycle_a_values[6] if cycle_a_values and len(cycle_a_values) > 6 else None,
        'CycleTime5': cycle_a_values[7] if cycle_a_values and len(cycle_a_values) > 7 else None,
        'CyclePSI1': cycle_a_values[8] if cycle_a_values and len(cycle_a_values) > 8 else None,
        'CyclePSI2': cycle_b_values[3] if cycle_b_values and len(cycle_b_values) > 3 else None,
        'CyclePSI3': cycle_b_values[4] if cycle_b_values and len(cycle_b_values) > 4 else None,
        'CyclePSI4': cycle_b_values[5] if cycle_b_values and len(cycle_b_values) > 5 else None,
        'CyclePSI5': cycle_b_values[6] if cycle_b_values and len(cycle_b_values) > 6 else None,
        'customerid1': set_id_values[3] if set_id_values and len(set_id_values) > 3 else None,
        'customerid2': set_id_values[4] if set_id_values and len(set_id_values) > 4 else None,
        'LC1_rate': set_id_values[5] if set_id_values and len(set_id_values) > 5 else None,
        'MaxCycles': set_id_values[6] if set_id_values and len(set_id_values) > 6 else None,
        'SM_DIR': set_id_values[7] if set_id_values and len(set_id_values) > 7 else None,
        'TP_Reverse': set_id_values[8] if set_id_values and len(set_id_values) > 8 else None,
        'SM_rpm': set_sm_values[3] if set_sm_values and len(set_sm_values) > 3 else None,
        'SM_rate': set_sm_values[4] if set_sm_values and len(set_sm_values) > 4 else None,
        'SM_timer': set_sm_values[5] if set_sm_values and len(set_sm_values) > 5 else None,
        'CycleDelay': set_sm_values[6] if set_sm_values and len(set_sm_values) > 6 else None,
        'TP_Max_Percent': set_sm_values[7] if set_sm_values and len(set_sm_values) > 7 else None,
        'f3scale': scale_f_values[3] if scale_f_values and len(scale_f_values) > 3 else None,
        'P1Scale': scale_f_values[4] if scale_f_values and len(scale_f_values) > 4 else None,
        'P5Scale': scale_f_values[5] if scale_f_values and len(scale_f_values) > 5 else None,
        'P4Scale': scale_f_values[6] if scale_f_values and len(scale_f_values) > 6 else None,
        't1scale': scale_t_values[3] if scale_t_values and len(scale_t_values) > 3 else None,
        't3scale': scale_t_values[4] if scale_t_values and len(scale_t_values) > 4 else None,
        'f1scale': scale_t_values[5] if scale_t_values and len(scale_t_values) > 5 else None,
        'f2scale': scale_t_values[6] if scale_t_values and len(scale_t_values) > 6 else None
    }
    

def clear_can_database():
    """
    This function:
    1. Checks if the database exists and if it has any data.
        If no data is found, logs a message indicating its empty.
    2. If not empty, attempts to back up the database. If backup fails, logs and error and stops.
    3. Removes the old database file
    4. Reinitializes the database to start fresh
    """
    backup_folder = os.path.join(base_path, "db_backups")
    os.makedirs(backup_folder, exist_ok=True)
    
    timestamp = datetime.now().strftime("(%Y-%m-%d_%H-%M-%S)")
    backup_filename = f"can_data_local_backup_{timestamp}.db"
    backup_path = os.path.join(backup_folder, backup_filename)
    
    # Check if the database exists
    if not os.path.exists(can_data_local_db):
        logging.warning("No existing database file found to backup or remove. Initializing a fresh database")
        initialize_databases()
        logging.info("Database reinitialized successfully.")
        return
    
    # Check if the database is empty
    # Define a list of CAN data tables (based on your schema) to check for data
    can_tables = [
        'FloPSI_0x0CFF000A', 'TempDigSet_0x0CFF010A', 'M1_OutputLC1_0x0CFF020A', 
        'M1_OutputSP_0x0CFF030A', 'M1Timers_0x0CFF040A', 'M1_Commands_0x0CFF050A', 
        'Set_ID_0x0CFF060A', 'Set_SM_0x0CFF070A', 'Set_CycleA_0x0CFF080A', 
        'Set_CycleB_0x0CFF090A', 'Set_ScaleT_0x0CFF0A0A', 'Set_ScaleF_0x0CFF0B0A', 
        'Scaled_M2_Data_0x0CFF0C0A', 'M2_Data1_0x0CFF0D14', 'M2_Data2_0x0CFF0E14', 
        'M1Ports_0x0CFF110A', 'M2Ports_0x0CFF0F14'
    ]
    
    db_empty = True
    try:
        conn = sqlite3.connect(can_data_local_db)
        cursor = conn.cursor()
        for table in can_tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            if count > 0:
                db_empty = False
                break
    except Exception as e:
        logging.error(f"Error checking if database is empty: {e}")
        # If we can't check emptiness, assume not empty and proceed.
        db_empty = False
    finally:
        if conn:
            conn.close()
    
    if db_empty:
        logging.info("Database is empty. No data to backup.")
    else:
        # Attempt to back up the current database
        try:
            shutil.copy2(can_data_local_db, backup_path)
            logging.info(f"Backed up database to {backup_path}")
        except Exception as e:
            logging.error(f"Failed to backup database: {e}")
            logging.error("Aborting clear_can_database operation to avoid data loss.")
            return # Stop if backup fails
    
    # Remove the old database
    try:
        os.remove(can_data_local_db)
        logging.info("Old database file removed.")
    except Exception as e:
        logging.error(f"Error removing old database file: {e}")
        
    # Reinitialize the databases
    initialize_databases()
    logging.info("Database reinitialized successfully.")