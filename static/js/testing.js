// testing.js

// Function to fetch live data for M1Ports and M2Ports tables
async function fetchPortsData() {
    try {
        const response = await fetch('/get_ports_data');
        if (!response.ok) throw new Error('Failed to fetch ports data');

        const data = await response.json();
        updatePortsTable('m1-ports-table-body', data.m1Ports);
        updatePortsTable('m2-ports-table-body', data.m2Ports);

    } catch (error) {
        console.error("Error fetching ports data:", error);
    }
}

// Function to download the database file
function downloadDatabase() {
    window.location.href = '/download_db';
}

// Function to confirm and delete the database
function confirmDeleteDatabase() {
    const confirmed = confirm("Are you sure you want to permanently delete the database? This action cannot be undone");

    if (confirmed) {
        fetch('/delete_db', { method: 'DELETE' })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    alert('Database deleted successfully.');
                } else {
                    alert('Failed to delete database');
                }
            })
            .catch(error => {
                console.error('Error deleting database:', error);
                alert('An error occured while deleting the database');
            });
    }
}

function confirmClearDatabase() {
    const confirmed = confirm("Are you sure you want to clear the database? This action cannot be undone.");

    if (confirmed) {
        fetch('/clear_db', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    alert('Database cleared successfully');
                } else {
                    alert('Failed to clear database');
                }
            })
            .catch(error => {
                console.error('Error clearing database:', error);
                alert('An error occured while clearing the database');
            });
    }
}

// Function to update the table body for M1 and M2 Ports
function updatePortsTable(tableBodyId, portsData) {
    const tableBody = document.getElementById(tableBodyId);
    tableBody.innerHTML = ''; // Clear existing table content

    if (!portsData || portsData.length === 0) {
        const row = document.createElement('tr');
        const cell = document.createElement('td');
        cell.colSpan = 2;
        cell.textContent = 'No data available';
        row.appendChild(cell);
        tableBody.appendChild(row);
        return;
    }

    // Get the most recent entry
    const latestData = portsData[0];

    // Exclude non-signal fields if necessary
    const excludeFields = ['id', 'timestamp', 'message_id', 'table_name'];

    for (const [signalName, statusValue] of Object.entries(latestData)) {
        if (excludeFields.includes(signalName)) continue;

        const row = document.createElement('tr');

        const signalCell = document.createElement('td');
        const formattedSignalName = formatSignalName(signalName);
        signalCell.textContent = formattedSignalName;
        row.appendChild(signalCell);

        const statusCell = document.createElement('td');

        // Apply multiplication for Supply Voltage signal
        let displayValue = statusValue;
        if (formattedSignalName.toLowerCase() === 'supply voltage') {
            const multipliedValue = parseFloat(statusValue) * 0.0339;
            displayValue = multipliedValue.toFixed(2);
        }

        statusCell.textContent = displayValue;

        const statusClass = getStatusClass(statusValue);
        if (statusClass) {
            statusCell.classList.add(statusClass);
        }

        row.appendChild(statusCell);

        tableBody.appendChild(row);
    }
}

// Helper function to format signal names
function formatSignalName(signalName) {
    // Convert from snake_case to readable text
    let formattedName = signalName.replace(/_/g, ' ').replace(/([a-z0-9])([A-Z])/g, '$1 $2').trim();

    // Handle specific cases if necessary
    if (formattedName.toLowerCase() === 'signal supply voltage') {
        formattedName = 'Supply Voltage';
    }

    return formattedName;
}

// Helper function to determine status class
function getStatusClass(value) {
    if (value === '0' || value === 0) {
        return 'status-ok';
    } else if (value === '1' || value === 1) {
        return 'status-error';
    } else {
        return null;
    }
}

// Fetch the ports data at a regular interval
setInterval(fetchPortsData, 2000); // Update every 2 seconds

// Initial fetch when the page loads
window.onload = function() {
    fetchPortsData();
};

// Start, Stop, and Emergency Stop functions
function start() {
    // Implement the start command
    fetch('/send_start_command', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                alert('Start command sent successfully');
            } else {
                alert('Failed to send start command');
            }
        })
        .catch(error => {
            console.error('Error sending start command:', error);
            alert('An error occurred while sending start command');
        });
}

function stop() {
    // Implement the stop command
    fetch('/send_stop_command', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                alert('Stop command sent successfully');
            } else {
                alert('Failed to send stop command');
            }
        })
        .catch(error => {
            console.error('Error sending stop command:', error);
            alert('An error occurred while sending stop command');
        });
}

function toggleEmergencyStop() {
    // Implement the emergency stop command
    fetch('/toggle_emergency_stop', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                alert('Emergency Stop toggled successfully');
            } else {
                alert('Failed to toggle Emergency Stop');
            }
        })
        .catch(error => {
            console.error('Error toggling Emergency Stop:', error);
            alert('An error occurred while toggling Emergency Stop');
        });
}
