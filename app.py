# Standard libraries
import os
import csv
import sqlite3
import logging
import threading
import time
import subprocess
import ipaddress
import sys
import shutil
from datetime import datetime

# Third-party libraries
from flask import Flask, render_template, jsonify, url_for, request, send_file
import pandas as pd
import dotenv
import can
import wexpect
from wexpect import ExceptionPexpect
from werkzeug.utils import safe_join

dotenv.load_dotenv()

# Local modules
from databaseManipulation import initialize_databases, write_to_db, get_live_data, log_data_to_csv, get_dvc_values, get_input_factor_from_db, save_header_data, clear_can_database
from decodeAndProcess import decode_message, process_can_data
from exportXLSX import process_csv_to_excel_from_file
import sendCommands


app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Optional envs:
ADMIN_REBOOT_KEY = os.getenv('ADMIN_REBOOT_KEY', '').strip()
_allowed = os.getenv('ADMIN_REBOOT_ALLOWED_SUBNETS', '127.0.0.1,192.168.1.0/24').split(',')
ADMIN_REBOOT_ALLOWED_SUBNETS = [s.strip() for s in _allowed if s.strip()]

# *RASPBERRY PI* Make sure to adjust the base_path to point at the env file or to the path in the pi

# Use absolute paths

base_path = os.getenv('csv_path')
network_base_path = os.getenv('NETWORK_BASE_PATH')
can_data_local_db = os.path.join(base_path, 'can_data_local.db')
settings_db = os.path.join(base_path, 'settings.db')

xlsx_dir = os.path.join(network_base_path, 'can_data_local.db')
db_backup_dir = os.path.join(network_base_path, 'db_backups')

db_lock = threading.Lock()

# Define this at the top of your file (after imports)
header_fields = [
    ('programName', 'Program Name'),
    ('description', 'Description'),
    ('employeeId', 'Employee ID'),
    ('compSet', 'Comp Set'),
    ('inputFactor', 'Input Factor'),
    ('inputFactorType', 'Input Factor Type'),
    ('serialNumber', 'Serial Number'), 
    ('customerId', 'Customer ID')
]



def process_can_data_locally():
    bus = None
    running = True 
    
    while running:
        try:
            if bus is None:
                logger.info("Attempting to connect to CAN interface...")
                bus = can.interface.Bus(channel='can0', bustype='socketcan')
                logger.info("Connected to CAN interface.")
            
            message = bus.recv(10) # Time out after 10 seconds
            
            if message:
                decoded_message_id, decoded_message = decode_message({
                    "arbitration": message.arbitration_id,
                    "data": message.data,
                    "timestamp": message.timestamp
                })
                
                if decoded_message:
                    write_to_db(decoded_message['table_name'], decoded_message)
                else:
                    logger.warning(f"Unknown CAN message ID: {decoded_message_id}")
                    
            else:
                time.sleep(0.1) # Short delay before retrying
        except can.CanError as e:
            logger.error(f"CAN bus error: {e}")
            bus = None # Reset bus on error
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            running = False # Stop on critical error
            

def _ip_allowed(remote_ip: str) -> bool:
    try:
        ip = ipaddress.ip_address(remote_ip)
        for net in ADMIN_REBOOT_ALLOWED_SUBNETS:
            # Allow single IP or CIDR
            if '/' in net:
                if ip in ipaddress.ip_network(net, strict=False):
                    return True
            else:
                if ip == ipaddress.ip_address(net):
                    return True
        return False
    except Exception:
        return False

def read_dvc_values(file_path):
    dvc_values = {}
    if os.path.exists(file_path):
        try:
            with open(file_path, mode='r') as csv_file:
                csv_reader = csv.DictReader(csv_file)
                for row in csv_reader:
                    dvc_values[row['variable']] = row['value']
        except Exception as e:
            logging.error(f"Error reading DVC values: {e}")
    return dvc_values

@app.route('/')
def index():
    try:
        input_factor = get_input_factor_from_db()
    except Exception as e:
        logging.error(f"Error fetching input factor: {e}")
        input_factor = None
    return render_template('index.html', input_factor=input_factor)

@app.route('/settings')
def settings():
    return render_template('settings.html')

@app.route('/reboot', methods=['POST'])
def reboot_pi():
    try:
        # Basic network gate
        remote_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if not _ip_allowed(remote_ip):
            app.logger.warning(f"Reboot blocked from IP {remote_ip}")
            return jsonify({"status": "error", "message": "Forbidden"}), 403
        
        # Optional header key gate
        if ADMIN_REBOOT_KEY:
            client_key = request.headers.get('X-Admin-Key', '')
            if client_key != ADMIN_REBOOT_KEY:
                app.logger.warning("Invalid X-Admin-Key for reboot")
                return jsonify({"status":"error","message":"Unauthorized"}), 401
            
        # --- Platform-aware behavior ---
        if sys.platform.startswith('win'):
            # Dev machine: do not attempt to reboot windows
            app.logger.info("Windows dev environment: simulating reboot (no-op).")
            return jsonify({"status": "ok", "message": "(dev) reboot simulated"}), 202
        
        # Linux (Pi) path:
        # Choose the most appropriate reboot command available
        cmd = None
        # Prefer systemctl if present 
        if shutil.which('systemctl'):
            # -i ignores inhibitors; can omit if you don't want that behavior 
            cmd = ['systemctl', 'reboot', '-i']
        elif shutil.which('/sbin/reboot'):
            cmd = ['/sbin/reboot']
        elif shutil.which('reboot'):
            cmd = ['reboot']
        else:
            return jsonify({"status": "error", "message": "No reboot command found on system"}), 500
        
        # Use sudo if available and not already root
        if os.geteuid() != 0 and shutil.which('sudo'):
            cmd = ['sudo'] + cmd
            
        app.logger.info(f"Initiating reboot with command: {' '.join(cmd)}")
        
        # Fire-and-forget reboot
        subprocess.Popen(cmd)
        return jsonify({"status": "ok", "message": "Reboot initiated"}), 202
    except Exception as e:
        app.logger.error(f"Reboot error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/save_ee_memory', methods=['POST'])
def save_ee_memory():
    data = request.json
    
    required_keys = [
        'customerid1', 'customerid2', 'SM_DIR', 'SM_rpm', 'SM_rate', 'SM_timer',
        'LC1_rate', 'MaxCycles', 'CycleTime1', 'CyclePSI1', 'CycleTime2', 'CyclePSI2',
        'CycleTime3', 'CyclePSI3', 'CycleTime4', 'CyclePSI4', 'CycleTime5', 'CyclePSI5',
        'CycleDelay', 't1scale', 't3scale', 'f1scale', 'f2scale', 'f3scale', 'TP_Reverse',
        'TP_Max_Percent', 'P1Scale', 'P5Scale', 'P4Scale'
    ]
    
    # Validate data
    missing_keys = [key for key in required_keys if key not in data]
    if missing_keys:
        return jsonify({'status': 'error', 'message': f'Missing keys: {missing_keys}'}), 400
    
    try:
        with db_lock:
            conn = sqlite3.connect(settings_db)
            cursor = conn.cursor()
            
            columns = ', '.join(required_keys)
            placeholders = ', '.join(['?'] * len(required_keys))
            sql = f'''
                INSERT OR REPLACE INTO EEMemoryValues ({columns})
                VALUES ({placeholders})
            '''
            values = [data[key] for key in required_keys]
            
            cursor.execute(sql, values)
            conn.commit()
            
        # After saving the data, send it over CAN bus
        sendCommands.send_ee_memory_variables()
        
        return jsonify({'status': 'success', 'message': 'EE-Memory values sent over CAN Bus successfully.'})
    
    except Exception as e:
        logging.error(f"Error saving EE memory: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to save EE memory values.'}), 500
    
    
@app.route('/get_signal_data')
def get_signal_data():
    signal = request.args.get('signal')
    if not signal:
        logging.error("No signal provided")
        return jsonify({"error": "No signal provided"}), 400
    
    signal = signal.strip().upper()
    
    table_mapping = {
        'S1': ('FloPSI_0x0CFF000A', 'signalDispS1'),
        'T1': ('TempDigSet_0x0CFF010A', 'signalT1'),
        'T3': ('TempDigSet_0x0CFF010A', 'signalT3'),
        'F1': ('Scaled_M2_Data_0x0CFF0C0A', 'signal_Scaled_F1'),
        'F2': ('FloPSI_0x0CFF000A', 'signalDispF2'),
        'F3': ('M1_Commands_0x0CFF050A', 'signal_Scaled_F3'),
        'P1': ('FloPSI_0x0CFF000A', 'signalDispP1'),
        'P2': ('Scaled_M2_Data_0x0CFF0C0A', 'signal_Scaled_P2'),
        'P3': ('M2_Data1_0x0CFF0D14', 'signalP3'),
        'P4': ('Scaled_M2_Data_0x0CFF0C0A', 'signal_Scaled_P4'),
        'P5': ('FloPSI_0x0CFF000A', 'signalDispP5'),
    }
    
    if signal not in table_mapping:
        logging.error(f"Invalid signal: {signal}")
        return jsonify({"error": "Invalid signal"}), 400
    
    table_name, column_name = table_mapping[signal]
    
    try:
        with sqlite3.connect(can_data_local_db) as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT timestamp, {column_name}
                FROM {table_name}
                ORDER BY timestamp DESC
                LIMIT 100
            """)
            data = cursor.fetchall()
            
        formatted_data = [
            {"timestamp": row[0], "value": row[1]} for row in data
        ]
        
        return jsonify(formatted_data)

    except Exception as e:
        logging.error(f"Error fetching signal data: {e}")
        return jsonify({"error": "Failed to fetch signal data"}), 500
    
def calculate_theo_flow_and_efficiency(s1, f1, input_factor):
    try:
        theo_flow = (s1 * input_factor) / 231
        efficiency = 0.0 if theo_flow == 0 else (f1 * 0.01 / theo_flow) * 100
        return round(theo_flow, 2), round(efficiency, 2)
    except Exception as e:
        logging.error(f"Error calculating Theo Flow and Efficiency: {e}")
        return 0.0, 0.0
    
@app.route('/get_live_data')
def get_live_data_route():
    try:
        input_factor = get_input_factor_from_db()
        data = get_live_data()
        
        s1 = float(data.get('s1', 0))
        f1 = float(data.get('f1', 0))
        theo_flow, efficiency = calculate_theo_flow_and_efficiency(s1, f1, input_factor)
        
        return jsonify({
            **data,
            'input_factor': input_factor,
            'theo_flow': theo_flow,
            'efficiency': efficiency
        })
    except Exception as e:
        app.logger.error(f"Error fetching live data: {e}")
        return jsonify({'error': 'Failed to fetch live data'}), 500
    
@app.route('/get_mode')
def get_mode():
    try:
        with sqlite3.connect(can_data_local_db) as conn:
            cursor = conn.cursor()
            query = "SELECT signalPB4 FROM TempDigSet_0x0CFF010A ORDER BY timestamp DESC LIMIT 1"
            cursor.execute(query)
            result = cursor.fetchone()
        if result:
            return jsonify({'signalPB4': result[0]})
        else:
            return jsonify({'error': 'No mode data found'}), 404
    except Exception as e:
        app.logger.error(f"Error fetching mode: {e}")
        return jsonify({'error': 'Failed to fetch mode'}), 500
    
@app.route('/get_csv_data', methods=['GET'])
def get_csv_data():
    try:
        csv_file_path = os.path.join(base_path, 'log_data.csv')
        if not os.path.exists(csv_file_path):
            return jsonify({"error": "CSV file not found"}), 404

        data = []
        with open(csv_file_path, 'r') as file:
            reader = csv.DictReader(file)
            data = list(reader)[-20:] # Get the last 20 entries
        
        return jsonify({"data": data})
    
    except Exception as e:
        app.logger.error(f"Error while processing CSV data: {e}")
        return jsonify({"error": "Internal server error"}), 500
    
@app.route('/get_header_data')
def get_header_data():
    try:
        with sqlite3.connect(settings_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT setting_name, setting_value FROM AppSettings")
            data = dict(cursor.fetchall())
        return jsonify(data)
    except Exception as e:
        app.logger.error(f"Error fetching header data: {e}")
        return jsonify({"error": "Failed to fetch header data"}), 500
    
@app.route('/send_start_command', methods=['POST'])
def send_start_command():
    try:
        thread = threading.Thread(target=sendCommands.send_start)
        thread.start()
        return jsonify({"status": "success", "message": "Start command sent"})
    except Exception as e:
        app.logger.error(f"Error sending start command: {e}")
        return jsonify({"status": "error", "message": "Failed to send start command"}), 500
    
@app.route('/get_dvc_values')
def get_dvc_values_route():
    try:
        dvc_values = get_dvc_values()
        return jsonify(dvc_values)
    except Exception as e:
        app.logger.error(f"Error fetching DVC values: {e}")
        return jsonify({"error": "Failed to fetch DVC values"}), 500
    
def fetch_header_data():
    with sqlite3.connect(settings_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT setting_name, setting_value FROM AppSettings WHERE setting_name IN ({seq})".format(
            seq=','.join(['?']*len(header_fields))
        ), [field[0] for field in header_fields])
        headers = dict(cursor.fetchall())
    return headers

def export_csv():
    try:
        # Fetch header data from the database
        headers = fetch_header_data()
        
        # Generate a timestamped filename
        timestamp = datetime.now().strftime("(%Y-%m-%d_%H-%M-%S)")
        updated_csv_filename = f"{timestamp}_log_data.csv"
        updated_csv_path = os.path.join(base_path, updated_csv_filename)
        
        # Create CSV content
        with open(updated_csv_path, 'w', newline='') as updated_csv:
            writer = csv.writer(updated_csv)
            
            # Write header information
            for field_key, display_name in header_fields:
                writer.writerow([display_name, headers.get(field_key, 'N/A')])
            
            writer.writerow([])  # Empty row for separation
            
            # Write column headers
            # NOTE: Theo Flow and Efficiency are NOT written here — exportXLSX
            # builds those as live Excel formulas so the spreadsheet stays dynamic.
            writer.writerow([
                "Date", "Time", "S1", "SP", "TP", "Cycle", "Cycle Timer", "LCSetpoint", 
                "LC Regulate", "Step", "F1", "F2", "F3", "T1", "T3", "P1", "P2", "P3", 
                "P4", "P5"
            ])
            
            # Process and write data rows
            csv_path = os.path.join(base_path, 'log_data.csv')
            if not os.path.exists(csv_path):
                raise FileNotFoundError("No data in CSV file to export.")
                
            with open(csv_path, 'r') as original_csv:
                reader = csv.DictReader(original_csv)
                for row in reader:
                    try:
                        # Scale F1 from centi-units to real units (* 0.01) HERE
                        # This is the ONE place F1 scaling happens in the export path.
                        raw_f1 = float(row.get('F1', 0))
                        scaled_f1 = raw_f1 * 0.01
                        
                        writer.writerow([
                            row.get('Date', ''),
                            row.get('Time', ''),
                            row.get('S1', ''),
                            row.get('SP', ''),
                            row.get('TP', ''),
                            row.get('Cycle', ''),
                            row.get('Cycle Timer', ''),
                            row.get('LCSetpoint', ''),
                            row.get('LC Regulate', ''),
                            row.get('Step', ''),
                            f"{scaled_f1:.2f}",
                            row.get('F2', ''),
                            row.get('F3', ''),
                            row.get('T1', ''),
                            row.get('T3', ''),
                            row.get('P1', ''),
                            row.get('P2', ''),
                            row.get('P3', ''),
                            row.get('P4', ''),
                            row.get('P5', ''),
                        ])
                    except (ValueError, KeyError) as e:
                        logging.error(f"Error processing row: {e}")
                        continue
        
        return updated_csv_path
    except Exception as e:
        logging.error(f"Error exporting CSV: {e}")
        raise
    
@app.route('/export_data', methods=['POST'])
def export_data():
    try:
        app.logger.info("Starting export_data process")
        
        # Generate the CSV file
        csv_file_path = export_csv()
        
        # Convert CSV to Excel
        logging.debug("Converting CSV to Excel")
        excel_file_path = process_csv_to_excel_from_file(csv_file_path)
        
        # Extract the filename from excel_file_path
        excel_filename = os.path.basename(excel_file_path)
        
        app.logger.info(f"Sending file with download_name: {excel_filename}")
        # Return the Excel file to the user
        return send_file(
            excel_file_path,
            as_attachment=True,
            download_name=excel_filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except FileNotFoundError as e:
        app.logger.error(f"File not found: {e}")
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        app.logger.error(f"Unexpected error during export: {e}")
        return jsonify({'error': 'Failed to export data'}), 500
    


def generate_csv_with_headers(headers):
    csv_path = os.path.join(base_path, 'log_data.csv')
    if not os.path.exists(csv_path):
        raise FileNotFoundError("No data in CSV file to export.")
    
    # Generate a timestamp filename
    time
    
@app.route('/update_header_data', methods=['POST'])
def update_header_data():
    data = request.json
    logging.info("Received header data for update")
    
    # Ensure all data fields are available
    required_fields = ['programName', 'description', 'compSet', 'inputFactor', 'inputFactorType', 'serialNumber', 'employeeId', 'customerId']
    missing_fields = [field for field in required_fields if not data.get(field)]
    if missing_fields:
        return jsonify({'status': 'error', 'message': f"Missing fields: {', '.join(missing_fields)}"}), 400
    
    # Save all header data to settings.db
    try:
        save_header_data(
            data['programName'],
            data['description'],
            data['compSet'],
            data['inputFactor'],
            data['inputFactorType'],
            data['serialNumber'],
            data['employeeId'],
            data['customerId']
        )
        return jsonify({'status': 'success'})
    except Exception as e:
        logging.error(f"Error saving header data: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to save header data'}), 500
    
allowed_file_extensions = ['.csv', '.xlsx']
    
@app.route('/get_ports_data')
def get_ports_data():
    try:
        # Ensure thread safety for database access if needed
        with db_lock:
            with sqlite3.connect(can_data_local_db) as conn:
                cursor = conn.cursor()
                
                # Fetch latest data from M1Ports
                cursor.execute('SELECT * FROM M1Ports_0x0CFF110A ORDER BY timestamp DESC LIMIT 10')
                m1_ports_rows = cursor.fetchall()
                m1_ports_columns = [desc[0] for desc in cursor.description]
                m1_ports_data = [dict(zip(m1_ports_columns, row)) for row in m1_ports_rows]
                
                # Fetch latest data from M2Ports
                cursor.execute('SELECT * FROM M2Ports_0x0CFF0F14 ORDER BY timestamp DESC LIMIT 10')
                m2_ports_rows = cursor.fetchall()
                m2_ports_columns = [desc[0] for desc in cursor. description]
                m2_ports_data = [dict(zip(m2_ports_columns, row)) for row in m2_ports_rows]
                
        return jsonify({'m1Ports': m1_ports_data, 'm2Ports': m2_ports_data})
    
    except Exception as e:
        logging.error(f"Error fetching ports data: {e}")
        return jsonify({"error": "Failed to fetch port data"}), 500
    
@app.route('/testing')
def testing():
    try:
        return render_template('testing.html')
    except Exception as e:
        logging.error(f"Error rendering testing.html: {e}")
        return jsonify({"error": "Failed to load testing page"}), 500
    
@app.route('/download_db')
def download_db():
    db_path = os.path.join(base_path, 'can_data_local.db')
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            return jsonify({'status': 'success', 'message': 'Database deleted successfully.'})
        except Exception as e:
            logging.error(f"Failed to delete database: {e}")
            return jsonify({'status': 'error', 'message': 'Failed to delete the database'}), 500
    else:
        return jsonify({'status': 'error', 'message': 'Database file not found.'}), 404
    
@app.route('/delete_db', methods=['DELETE'])
def delete_db():
    db_path = os.path.join(base_path, 'can_data_local.db')
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            return jsonify({'status': 'success', 'message': 'Database deleted successfully.'})
        except Exception as e:
            logging.error(f"Failed to delete database: {e}")
            return jsonify({'status': 'error', 'message': 'Failed to delete database'}), 500
    else:
        return jsonify({'status': 'error', 'message': 'Database file not found.'}), 404
    
@app.route('/clear_db', methods=['POST'])
def clear_db():
    try:
        with db_lock:
            clear_can_database()
        
        return jsonify({'status': 'success', 'message': 'Database cleared and reinitialized.'})
    except Exception as e:
        logging.error(f"Failed to clear and reinitialize database: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to clear and reinitialize database.'})
    

@app.route('/past_tests')
def past_tests():
    # Directory where .xlsx files are saved
    directory = base_path
    
    # List all .xlsx files
    xlsx_files = [f for f in os.listdir(directory) if f.lower().endswith('.xlsx')]
    
    # Sort files by modified time 
    # Get absolute path and stat, then sort by modification time descending
    xlsx_files = sorted(xlsx_files, key=lambda f: os.path.getmtime(os.path.join(directory, f)), reverse=True)
    
    files_info = []
    for f in xlsx_files:
        full_path = os.path.join(directory, f)
        mod_time = os.path.getmtime(full_path)
        # Format the modification time
        from datetime import datetime
        mod_time_str = datetime.fromtimestamp(mod_time).strftime("%B %d, %Y at %I:%M:%S %p")
        
        files_info.append({
            'filename': f,
            'modified_time': mod_time_str
        })
        
    # List all .db backups in db_backup folder
    backup_folder = os.path.join(directory, 'db_backups')
    db_files_info = []
    if os.path.exists(backup_folder):
        db_files = [f for f in os.listdir(backup_folder) if f.lower().endswith('.db')]
        db_files = sorted(db_files, key=lambda f: os.path.getmtime(os.path.join(backup_folder, f)), reverse=True)
        
        for f in db_files:
            full_path = os.path.join(backup_folder, f)
            mod_time = os.path.getmtime(full_path)
            mod_time_str = datetime.fromtimestamp(mod_time).strftime("%B %d, %Y at %I:%M:%S %p")
            db_files_info.append({
                'filename': f,
                'modified_time': mod_time_str
            })
            
    return render_template('past_tests.html', files=files_info, db_files=db_files_info)

@app.route('/download_test/<filename>')
def download_test(filename):
    # Validate and serve the file
    # Ensure no directory traversal:
    if '..' in filename or filename.startswith('/'):
        return "Invalid filename", 400
    
    # Construct safe path
    full_path = safe_join(base_path, filename)
    if not os.path.exists(full_path):
        # If not in the main folder, try db_backups folder
        backup_folder = os.path.join(base_path, 'db_backups')
        full_path = os.path.join(backup_folder, filename)
        if not os.path.exists(full_path):
            return "File not found", 404

    # Determine mimetype based on extension
    if filename.lower().endswith('.xlsx'):
        mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    elif filename.lower().endswith('.db'):
        mimetype = 'application/octet-stream' # Generic binary for .db files
    else:
        mimetype = 'application/octet-stream'
    
    return send_file(full_path, as_attachment=True, download_name=filename, mimetype=mimetype)

@app.route('/delete_file/<filename>', methods=['DELETE'])
def delete_file(filename):
    # Validate filename
    if '..' in filename or filename.startswith('/'):
        return jsonify({'status': 'error', 'message': 'Invalid filename'}), 400
    
    # Attempt to delete from main directory first
    full_path = os.path.join(base_path, filename)
    if not os.path.exists(full_path):
        # Try db_backups folder
        backup_folder = os.path.join(base_path, 'db_backups')
        full_path = os.path.join(backup_folder, filename)
        if not os.path.exists(full_path):
            return jsonify({'status': 'error', 'message': 'File not found'}), 404
    
    try:
        os.remove(full_path)
        logging.info(f"Deleted file: {full_path}")
        return jsonify({'status': 'success', 'message': 'File deleted successfully.'})
    except Exception as e:
        logging.error(f"Error deleting file: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to delete file'}), 500
    
@app.route('/clear_data_table', methods=['POST'])
def clear_data_table():
    logging.info("Received request to clear data table.")
    try:
        csv_path = os.path.join(base_path, 'log_data.csv')
        logging.debug(f"CSV path: {csv_path}")
        
        if not os.path.exists(csv_path):
            logging.warning("log_data.csv does not exist.")
            return jsonify({"status": "error", "message": "No data table found (log_data.csv does not exist)."}), 404
        
        # The header line that must remain
        header_line = "Date,Time,S1,SP,TP,Cycle,Cycle Timer,LCSetpoint,LC Regulate,Step,F1,F2,F3,T1,T3,P1,P2,P3,P4,P5\n"
        
        logging.debug("Attempting to overwrite log_data.csv with only the header line.")
        # Overwrite the file with only the header line
        with open(csv_path, 'w', newline='', encoding='utf-8') as csv_file:
            csv_file.write(header_line)
        logging.info("Data table cleared successfully, header retained.")
            
        return jsonify({"status": "success", "message": "Data table cleared, header retained."})
    except Exception as e:
        logging.error(f"Error clearing data table: {e}")
        return jsonify({"status": "error", "message": "Failed to clear data table."}), 500

            
def main():
    """
    Main application function that starts the Flask app in the main thread.
    """
    
    clear_can_database()
    # Configuration from environment variables
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    port = int(os.getenv('FLASK_PORT', '8000'))
    
    can_data_thread = threading.Thread(target=process_can_data)
    can_data_thread.daemon = True
    can_data_thread.start()
    
    logging_thread = threading.Thread(target=log_data_to_csv)
    logging_thread.daemon = True
    logging_thread.start()
    
    # Run the Flask web interface
    app.run(debug=debug_mode, port=port) # *RASPBERRY PI* add host='192.168.1.90' between debug_mode and port 
    #app.run(debug=debug_mode, host='192.168.1.90', port=port)
    
if __name__ == '__main__':
    main()