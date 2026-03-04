import can
import sqlite3
import os

# Path to the settings.db
settings_db = os.path.join(r'/home/devteam/Python/NewCanBusWebInterface/TestStandWebInterface/base/', 'settings.db')

def get_ee_memory_values():
    """
    Retrieves EE-Memory values from settings.db
    Returns a dictionary with EE-Memory variables
    """
    conn = sqlite3.connect(settings_db)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM EEMemoryValues ORDER BY id DESC LIMIT 1')
    ee_memory_row = cursor.fetchone()
    
    conn.close()
    
    if not ee_memory_row:
        return None
    
    # Column names matching your settings.html fields
    columns = [
        "customerid1", "customerid2", "SM_DIR", "SM_rpm", "SM_rate",
        "SM_timer", "LC1_rate", "MaxCycles", "CycleTime1", "CyclePSI1",
        "CycleTime2", "CyclePSI2", "CycleTime3", "CyclePSI3",
        "CycleTime4", "CyclePSI4", "CycleTime5", "CyclePSI5",
        "CycleDelay", "t1scale", "t3scale", "f1scale", "f2scale",
        "f3scale", "TP_Reverse", "TP_Max_Percent", "P1Scale",
        "P5Scale", "P4Scale"
    ]
    
    return dict(zip(columns, ee_memory_row[1:]))

# function to build the data array for CAN messages based on arbitration ID
def build_ee_memory_data(arbitration_id, ee_memory_values):
    if arbitration_id == 0x0CFF121E:
        return [
            (int(ee_memory_values.get('customerid1', 0))&0xFF),
            ((int(ee_memory_values.get('customerid1', 0))&0xFF00)/256),
            (int(ee_memory_values.get('customerid2', 0))&0xFF),
            ((int(ee_memory_values.get('customerid2', 0))&0xFF00)/256),
            (int(ee_memory_values.get('LC1_rate', 0))&0xFF),
            ((int(ee_memory_values.get('LC1_rate', 0))&0xFF00)/256),
            int(ee_memory_values.get('MaxCycles', 0)),
            (int(ee_memory_values.get('SM_DIR', 0))+(int(ee_memory_values.get('TP_Reverse', 0))<<1)),
            #^^^combining these 2 booleans into the same byte^^^
            0, 0 # Padding for remaining bytes
        ]
    elif arbitration_id == 0x0CFF131E:
        return [
            (int(ee_memory_values.get('eeSM_rpm', 0))&0xFF),
            ((int(ee_memory_values.get('eeSM_rpm', 0))&0xFF00)/256),
            (int(ee_memory_values.get('eeSM_rate', 0))&0xFF),
            ((int(ee_memory_values.get('eeSM_rate', 0))&0xFF00)/256),
            (int(ee_memory_values.get('eeCycledelay', 0))&0xFF),
            ((int(ee_memory_values.get('eeCycledelay', 0))&0xFF)/256),
            (int(ee_memory_values.get('eeTP_Max_Percent', 0))&0xFF),
            ((int(ee_memory_values.get('eeTP_Max_Percent', 0))&0xFF00)/256),
            0, 0
        ]
    elif arbitration_id == 0x0CFF141E:
        return [
            int(ee_memory_values.get('eeCycleTime1', 0)),
            int(ee_memory_values.get('eeCycleTime2', 0)),
            int(ee_memory_values.get('eeCycleTime3', 0)),
            int(ee_memory_values.get('eeCycleTime4', 0)),
            (int(ee_memory_values.get('eeCyclePSI1', 0))&0xFF),
            ((int(ee_memory_values.get('eeCyclePSI1', 0))&0xFF00)/256),
            0, 0
        ]
    elif arbitration_id == 0x0CFF151E:
        return [
            (int(ee_memory_values.get('eeCyclePSI2', 0))&0xFF),
            ((int(ee_memory_values.get('eeCyclePSI2', 0))&0xFF00)/256),
            (int(ee_memory_values.get('eeCyclePSI3', 0))&0xFF),
            ((int(ee_memory_values.get('eeCyclePSI3', 0))&0xFF00)/256),
            (int(ee_memory_values.get('eeCyclePSI4', 0))&0xFF),
            ((int(ee_memory_values.get('eeCyclePSI4', 0))&0xFF00)/256),
            (int(ee_memory_values.get('eeCyclePSI5', 0))&0xFF),
            ((int(ee_memory_values.get('eeCyclePSI5', 0))&0xFF00)/256),
            0, 0
        ]
    elif arbitration_id == 0x0CFF161E:
        return [
            (int(ee_memory_values.get('eet1scale', 0))&0xFF),
            ((int(ee_memory_values.get('eet3scale', 0))&0xFF00)/256),
            (int(ee_memory_values.get('eef1scale', 0))&0xFF),
            ((int(ee_memory_values.get('eef2scale', 0))&0xFF00)/256),
            0, 0
        ]
    elif arbitration_id ==  0x0CFF171E:
        return [
            (int(ee_memory_values.get('eef3scale', 0))&0xFF),
            ((int(ee_memory_values.get('eef3scale', 0))&0xFF00)/256),
            (int(ee_memory_values.get('eeP1Scale', 0))&0xFF),
            ((int(ee_memory_values.get('eeP1Scale', 0))&0xFF00)/256),
            (int(ee_memory_values.get('eeP5Scale', 0))&0xFF),
            ((int(ee_memory_values.get('eeP5Scale', 0))&0xFF00)/256),
            (int(ee_memory_values.get('eeP4Scale', 0))&0xFF),
            ((int(ee_memory_values.get('eeP4Scale', 0))&0xFF00)/256),
            0, 0
        ]
    else:
        return [0] * 8
    
    
# bus.sendPeriodic
    
    
def send_ee_memory_variables():
    ee_memory_values = get_ee_memory_values()
    if ee_memory_values is None:
        print("No EE-Memory values found.")
        return
    
    arbitration_ids = [0x0CFF121E, 0x0CFF131E, 0x0CFF141E, 0x0CFF151E, 0x0CFF161E, 0x0CFF171E]
    
    bus = get_can_bus()
    
    if bus:
        # can.BusABC().stop_all_periodic_tasks()
        for arb_id in arbitration_ids:
            data = build_ee_memory_data(arb_id, ee_memory_values)
            # print(arb_id)
            # print(data)
            data = [int(x) for x in data] # each item in data needs to be read as an int.
            msg = can.Message(arbitration_id=arb_id, data=data, is_extended_id=True)
            try:
                bus.send_periodic(msg,.2)
                bus.send(msg)
                print(f"EE-Memory data sent for arbitratio ID {hex(arb_id)}")
            except can.CanError:
                print(f"EE-Memory message NOT sent for arbitration ID {hex(arb_id)}")
            send_save_settings(bus)
    else:
        print("Can bus initialization failed.")


def get_can_bus():
    try:
        bus = can.Bus(interface='socketcan', channel='can0', bitrate=500000)
        return bus
    except Exception as e:
        print(f"Failed to initialize CAN bus: {e}")
        return None
    

def send_start(bus):
    
    if bus:
         
            msg = can.Message(
                arbitration_id=0x0CFF101E, data=[1, 0, 0, 0, 0, 0, 0, 0], is_extended_id=True
            )
            
            try:
                bus.send(msg)
                print(f"Message sent on {bus.channel_info}")
            except can.CanError as e:
                print("Start message NOT sent. Error: {e}")
                
def send_stop(bus):
    if bus:
        
            msg = can.Message(
                arbitration_id=0x0CFF101E, data=[2, 0, 0, 0, 0, 0, 0, 0], is_extended=True
            )
            try:
                bus.send(msg)
                print(f"Message sent on {bus.channel_info}")
            except can.CanError as e:
                print("Stop message NOT sent. Error: {e}")
                        
def send_estop(bus):
    if bus:
        
        msg = can.Message(
            arbitration_id=0x0CFF101E, data=[4, 0, 0, 0, 0, 0, 0, 0], is_extended_id=True
        )
        
        try:
            bus.send(msg)
            print(f"Message send on {bus.channel_info}")
        except can.CanError as e:
            print("EStop message NOT sent. Error: {e}")
            
    
    
def send_save_settings(bus):
    if bus:
        msg = can.Message(
            arbitration_id=0x0CFF101E, data=[64, 0, 0, 0, 0, 0, 0, 0], is_extended_id=True
            )
        try:
            bus.send_periodic(msg,.1,duration=2)
            print(f"Save Settings Message sent on {bus.channel_info}")
        except can.CanError as e:
            print("Save Settings NOT sent. Error: {e}")
                    
                    
        
if __name__ == "__main__":
    bus = get_can_bus()
    if bus:
        # send_start(bus)
        # send_stop(bus)
        # send_estop(bus)
        send_ee_memory_variables()
        # send_save_settings(bus)
