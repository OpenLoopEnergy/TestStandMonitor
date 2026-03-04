// Global variables
let inputFactor; 
let csvGenerated = false;
let retryCount = 0;
let previousMode = null;
let hasPromptedForAutomatic = false;
let hlsInstance = null;

window.fetchMode = fetchMode;

// Chart-related variables
const yAxisMaxMapping = {
    'S1': 2000,
    'T1': 200,
    'T3': 200,
    'F1': 200,
    'F2': 32,
    'F3': 200,
    'P1': 6000,
    'P2': 600,
    'P3': 1000,
    'P4': 100,
    'P5': 6000,
    'TheoFlow': 100,
    'Efficiency': 110
};

let myChart = null;
let currentSignal = 'S1';
let theoFlowData = [];
let efficiencyData = [];
let theoFlowLabels = [];
let efficiencyLabels = [];

// Ensure DOMContentLoaded fires and code runs
document.addEventListener('DOMContentLoaded', () => {

    initializeButtons();
    initializeHeaderButtons();
    setupSignalSwitching();
    loadHeaderData();
    fetchMode();
    setInterval(fetchMode, 5000);
    fetchLiveData();
    setInterval(fetchLiveData, 500); // Update live data every 0.5 seconds
    setInterval(updateGraph, 5000);   // Update graph every 5 seconds
    setInterval(fetchCSVData, 5000);  // Fetch CSV data every 5 seconds
    setInterval(checkTrendingStatus, 5000); // Check trending status every 5 seconds
    //initHlsStream();

    // Initialize Bootstrap toasts
    $('.toast').toast({
        autohide: true,
        delay: 3000
    });

    // Initalize video panning
    //initVideoPanning();

    // const audio = document.getElementById("audio-stream");
    // const toggle = document.getElementById("audio-toggle");

    // if (audio && toggle) {
    //     // Start muted to bypass autoplay restrictions
    //     audio.muted = true;
    //     toggle.classList.add("muted");

    //     function connectAudio(attempts = 10, delay = 1000) {
    //         audio.load();
    //         audio.play().catch
    //     }

    //     // Load the stream immediately
    //     audio.load()

    //     // Error handling
    //     audio.addEventListener('error', (e) => {
    //         console.error("Audio error:", e);
    //         setTimeout(() => audio.load(), 1000); // Retry after 1 second
    //     });
    //     audio.addEventListener('stalled', () => {
    //         console.warn("Audio stalled, retrying...");
    //         audio.load();
    //     });
    //     audio.addEventListener('playing', () => {
    //         console.log("Audio playing");
    //     });

    //     toggle.addEventListener("click", () => {
    //         if (audio.muted) {
    //             // Unmute and play
    //             audio.muted = false;
    //             audio.play().catch(err => {
    //                 console.error("Play failed:", err);
    //             });
    //             toggle.classList.remove("muted");
    //             toggle.classList.add("unmuted");
    //         } else {
    //             // Mute
    //             audio.muted = true;
    //             toggle.classList.remove("unmuted");
    //             toggle.classList.add("muted");
    //         }
    //     });
    // } else {
    //     console.warn("Audio or toggle element not found");
    // }
    // // Refresh the stream every 5 minutes
    // setInterval(() => {
    //     console.log("Refreshing the HLS stream...");
    //     initHlsStream();
    // }, 5 * 60 * 1000);
    
});

// function initHlsStream() {
//     // Grab the video element and HLS URL
//     const video = document.getElementById('liveVideo');
//     const hlsUrl = 'http://192.168.1.90/stream.m3u8?t=' + new Date().getTime();

//     if (!video) {
//         console.error("Video element not found");
//         return;
//     }

//     // If we've already created an Hls instance, destroy it before making a new one
//     if (hlsInstance) {
//         hlsInstance.destroy();
//         hlsInstance = null;
//     }

//     // Check if the browser supports native HLS
//     if (video.canPlayType('application/vnd.apple.mpegurl')) {
//         video.src = hlsUrl;
//         video.play().catch(err => console.error("Native HLS play() failed:", err));
//     }
//     else if (Hls.isSupported() && video) {
//         // Otherwise, use hls.js
//         hlsInstance = new Hls({
//             //debug: true,
//             maxBufferLength: 10, // Reduce buffering for live
//             liveSyncDurationCount: 3
//         });

//         hlsInstance.loadSource(hlsUrl);
//         hlsInstance.attachMedia(video);
//         hlsInstance.on(Hls.Events.MANIFEST_PARSED, () => {
//             video.play().catch(err => console.error("hls.js video play() failed:", err));
//         });
//         hlsInstance.on(Hls.Events.ERROR, (event, data) => {
//             if (data.fatal) {
//                 console.error("Fatal HLS error:", data.details);
//             }
//         });
//     }
//     else {
//         console.error("This browser does not support HLS")
//     }
// }

/**
 * Initializes the Export and Clear Data Table buttons with event listeners.
 */
function initializeButtons() {
    const clearDataTableButton = document.getElementById('clear-data-table-button');
    if (clearDataTableButton) {
        clearDataTableButton.addEventListener('click', () => {
            const confirmed = confirm("Are you sure you want to clear the data table? This action cannot be undone and you won't be able to export the cleared data.");

            if (confirmed) {
                fetch('/clear_data_table', { method: 'POST' })
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'success') {
                            showSuccess('Data table cleared successfully. The heading is still intact.');
                            // Refresh the page
                            location.reload();
                        } else {
                            showError("Failed to clear the data table: " + data.message);
                        }
                    })
                    .catch(error => {
                        console.error('Error clearing data table:', error);
                        showError('An error occurred while clearing the data table.');
                    });
            } else {
                console.log("User canceled clearing the data table.");
            }
        });
    } else {
        console.warn("clear-data-table-button not found");
    }

    const exportDataButton = document.getElementById('export-data-button');
    if (exportDataButton) {
        exportDataButton.addEventListener('click', async () => {
            try {
                const response = await fetch('/export_data', { method: 'POST' });
                
                if (!response.ok) {
                    throw new Error('Failed to export data');
                }

                // Extract filename from Content-Disposition header
                let filename = 'exported_data1.xlsx'; // Fallback if no header is found
                const contentDisposition = response.headers.get('Content-Disposition');

                if (contentDisposition) {
                    const match = contentDisposition.match(/filename="?([^;]+)"?/);
                    if (match && match[1]) {
                        filename = match[1].trim();
                    }
                }

                const blob = await response.blob();

                // Create a temporary download link for the blob
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;

                // If the server doesn't send a filename, provide a default name
                a.download = filename;
                document.body.appendChild(a);
                a.click();

                // Clean up 
                window.URL.revokeObjectURL(url);
                a.remove();
                
                showSuccess('Data exported successfully!');
            } catch (error) {
                console.error('Error exporting data:', error);
                showError('An error occurred while exporting data: ' + error.message);
            }
        });
    } else {
        console.warn("export-data-button not found");
    }
}

/**
 * Initializes the Edit and Save Header buttons with event listeners.
 */
function initializeHeaderButtons() {
    const editHeaderButton = document.getElementById("edit-header-button");
    const saveHeaderButton = document.getElementById("save-header-button");

    if (editHeaderButton && saveHeaderButton) {
        editHeaderButton.addEventListener("click", toggleEditHeader);
        saveHeaderButton.addEventListener("click", saveHeader);
    } else {
        console.warn("Edit or Save header buttons not found");
    }
}

/**
 * Toggles the editability of the header fields.
 */
function toggleEditHeader() {
    const headerFields = [
        "headerProgramName",
        "headerDescription",
        "headerCompSet",
        "headerInputFactor",
        "headerSerialNumber",
        "headerEmployeeId",
        "headerCustomerId"
    ];

    headerFields.forEach(id => {
        const elem = document.getElementById(id);
        if (elem) {
            elem.readOnly = !elem.readOnly;
        }
    });

    const selectElement = document.getElementById("headerInputFactorType");

    if (selectElement) {
        if (selectElement.disabled) {
            selectElement.disabled = false;
            selectElement.classList.remove("disabled-dropdown");
            selectElement.classList.add("enabled-dropdown");
        } else {
            selectElement.disabled = true;
            selectElement.classList.remove("enabled-dropdown");
            selectElement.classList.add("disabled-dropdown");
        }
    }

    const editButton = document.getElementById("edit-header-button");
    const saveButton = document.getElementById("save-header-button");

    if (editButton && saveButton) {
        if (editButton.style.display === "none") {
            editButton.style.display = "inline-block";
            saveButton.style.display = "none";
        } else {
            editButton.style.display = "none";
            saveButton.style.display = "inline-block";
        }
    }
}

/**
 * Saves the updated header information to the server.
 */
async function saveHeader() {
    const programNameElem = document.getElementById("headerProgramName");
    const descriptionElem = document.getElementById("headerDescription");
    const compSetElem = document.getElementById("headerCompSet");
    const inputFactorElem = document.getElementById("headerInputFactor");
    const inputFactorTypeElem = document.getElementById("headerInputFactorType");
    const serialNumberElem = document.getElementById("headerSerialNumber");
    const employeeIdElem = document.getElementById("headerEmployeeId");
    const customerIdElem = document.getElementById("headerCustomerId");

    if (!programNameElem || !descriptionElem || !compSetElem || !inputFactorElem || !inputFactorTypeElem || !serialNumberElem || !employeeIdElem || !customerIdElem) {
        console.error("One or more header input fields are missing.");
        return;
    }

    const programName = programNameElem.value.trim();
    const description = descriptionElem.value.trim();
    const compSet = parseInt(compSetElem.value, 10);
    const inputFactor = parseFloat(inputFactorElem.value);
    const inputFactorType = inputFactorTypeElem.value;
    const serialNumber = parseInt(serialNumberElem.value, 10);
    const employeeId = parseInt(employeeIdElem.value, 10);
    const customerId = parseInt(customerIdElem.value, 10);

    // Basic validation
    if (!programName || !description || isNaN(compSet) || isNaN(inputFactor) || !["cu/in", "cu/cm"].includes(inputFactorType) || isNaN(serialNumber) || isNaN(employeeId) || isNaN(customerId)) {
        showError('All fields are required and must be correctly formatted.');
        return;
    }

    try {
        const response = await fetch('/update_header_data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ programName, description, compSet, inputFactor, inputFactorType, serialNumber, employeeId, customerId })
        });

        if (!response.ok) {
            console.error("Failed to send save request:", response.statusText);
            throw new Error("Failed to send save request");
        }

        const data = await response.json();
        if (data.status === 'success') {
            showSuccess('Header updated successfully');
            toggleEditHeader(); 
        } else {
            showError("Failed to update header: " + data.message || "Unknown error");
        }
    } catch (error) {
        console.error("Error updating header:", error);
        showError("An error occurred while updating the header.");
    }
}

/**
 * Fetches live data from the server and updates the UI accordingly.
 */
async function fetchLiveData() {
    try {
        const response = await fetch('/get_live_data');
        if (!response.ok) throw new Error('Failed to fetch live data');

        const data = await response.json();
        if (data.error) throw new Error(data.error);

        // Reset retry count on success
        retryCount = 0;

        const theoflow = (data.s1 * inputFactor) / 231;
        const f1 = (data.f1 * 0.01);
        const efficiency = theoflow !== 0 ? (((f1 / theoflow) * 100)) : 0;

        theoFlowData.push(theoflow);
        efficiencyData.push(efficiency);
        const currentTime = moment().format('YYYY-MM-DDTHH:mm:ss');
        theoFlowLabels.push(currentTime);
        efficiencyLabels.push(currentTime);

        // Limit data points
        if (theoFlowData.length > 100) {
            theoFlowData.shift();
            theoFlowLabels.shift();
        }
        if (efficiencyData.length > 100) {
            efficiencyData.shift();
            efficiencyLabels.shift();
        }

        // Update page elements
        document.getElementById('s1').textContent = `${data.s1} RPM`;
        document.getElementById('sp').textContent = `${data.sp} RPM`;
        document.getElementById('tp').textContent = `${Math.floor(data.tp / 10.23)}%`;
        document.getElementById('theoflow').textContent = `${theoflow.toFixed(2)} GPM`;
        document.getElementById('efficiency').textContent = `${efficiency.toFixed(2)}%`;
        document.getElementById('delay').textContent = `${(data.delay * 0.01).toFixed(2)} s`;
        document.getElementById('trending').textContent = data.trending ? 'True' : 'False';
        document.getElementById('cycle').textContent = `${data.cycle}`;
        document.getElementById('cycleTimer').textContent = `${(data.cycleTimer / 100).toFixed(2)} s`;
        document.getElementById('lcSetpoint').textContent = `${data.lcSetpoint} PSI`;
        document.getElementById('lcRegulate').textContent = data.lcRegulate ? 'True' : 'False';
        document.getElementById('step').textContent = data.step;
        document.getElementById('t1').textContent = `${(data.t1 * 0.1).toFixed(1)} F`;
        document.getElementById('t3').textContent = `${(data.t3 * 0.1).toFixed(1)} F`;
        document.getElementById('f1').textContent = `${f1.toFixed(2)} GPM`;
        document.getElementById('f2').textContent = `${(data.f2 * 0.01).toFixed(2)} GPM`;
        document.getElementById('f3').textContent = `${(data.f3 * 0.01).toFixed(2)} GPM`;
        document.getElementById('p1').textContent = `${data.p1} PSI`;
        document.getElementById('p5').textContent = `${data.p5} PSI`;
        document.getElementById('p2').textContent = `${data.p2} PSI`;
        document.getElementById('p3').textContent = `${data.p3} PSI`;
        document.getElementById('p4').textContent = `${data.p4} PSI`;
    } catch (error) {
        console.error("Error fetching live data:", error);

        retryCount++;
        if (retryCount <= 10) {
            setTimeout(fetchLiveData, 2000); // Retry after 2 seconds
        } else {
            console.error("Max retries reached. Live data not available.");
        }
    }
}

setInterval(fetchLiveData, 500); // Update live data every 0.5 seconds

/**
 * Creates or updates the Chart.js line chart.
 * @param {Array} labels - Array of labels (timestamps).
 * @param {Array} data - Array of data points.
 * @param {number} yMax - Maximum value for the Y-axis.
 */
function createChart(labels, data, yMax) {
    const ctx = document.getElementById('myChart').getContext('2d');

    // Retrieve CSS variables
    const rootStyles = getComputedStyle(document.documentElement);
    const chartPrimary = rootStyles.getPropertyValue('--chart-primary').trim() || '#EB1C23';
    const chartSecondary = rootStyles.getPropertyValue('--chart-secondary').trim() || 'rgba(185,33,40,0.1)';
    const chartHoverBg = rootStyles.getPropertyValue('--chart-hover-bg').trim() || 'rgba(26,115,232,0.7)';
    const chartPointHoverBg = rootStyles.getPropertyValue('--chart-point-hover-bg').trim() || 'rgba(205,233,143,0.7)';
    const chartPointHoverBorder = rootStyles.getPropertyValue('--chart-point-hover-border').trim() || 'rgba(144,78,226,0.7)';

    if (myChart) {
        myChart.destroy(); 
    }

    // Create gradient for the dataset background
    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, chartPrimary);
    gradient.addColorStop(1, chartSecondary);

    // Define the multiply blend mode plugin
    const multiplyBlend = {
        id: 'multiplyBlend',
        beforeDatasetsDraw(chart, args, options) {
            chart.ctx.globalCompositeOperation = 'multiply';
        },
        afterDatasetsDraw(chart, args, options) {
            chart.ctx.globalCompositeOperation = 'source-over';
        },
    };

    myChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: `${currentSignal} Data`,
                data: data,
                borderColor: 'var(--primary-red)', // Use CSS variable
                backgroundColor: gradient,         // Use CSS variable
                hoverBackgroundColor: chartHoverBg, 
                pointHoverBackgroundColor: chartPointHoverBg,
                pointHoverBorderColor: chartPointHoverBorder,
                borderWidth: 2,
                fill: true,
                pointRadius: 3,
                tension: 0.4,

                // New lines to control the default (non-hover) point colors
                pointBackgroundColor: chartPrimary, 
                pointBorderColor: '#FFFFFF',
            }]
        },
        options: {
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'second',
                        stepSize: 1,
                        tooltipFormat: 'YYYY-MM-DDTHH:mm:ss',
                    },
                    ticks: {
                        source: 'auto',
                        autoSkip: true,
                        color: 'rgb(255,255,255)', // white
                    },
                    grid: {
                        color: 'rgb(86,86,86)', // gray
                    },
                    display: true,
                },
                y: {
                    ticks: {
                        color: 'rgb(255,255,255)', // White
                    },
                    grid: {
                        color: 'rgb(86,86,86)', // Gray
                    },
                    beginAtZero: true,
                    max: yMax,
                    display: true,
                }
            },
            animation: false,
            plugins: {
                legend: {
                    display: true,
                    labels: {
                        boxWidth: 20,
                        color: 'rgb(255,255,255)', // White
                    }
                },
                tooltip: {
                    backgroundColor: 'rgb(255,0,0,0.8)', // Red
                    bodyColor: 'rgb(255,255,255)',       // White
                    mode: 'index',
                    intersect: false,
                    titleColor: 'rgb(255,255,255)',      // White
                }
            },
            elements: {
                point: {
                    hitRadius: 5,
                }
            }
        },
        plugins: [multiplyBlend],
    });
}


/**
 * Updates the chart based on the current signal.
 */
async function updateGraph() {
    try {
        let values = [];
        let labels = [];

        if (currentSignal === 'TheoFlow') {
            values = theoFlowData;
            labels = theoFlowLabels;
        } else if (currentSignal === 'Efficiency') {
            values = efficiencyData;
            labels = efficiencyLabels;
        } else {
            const signalResponse = await fetch(`/get_signal_data?signal=${currentSignal}`);
            const signalData = await signalResponse.json();

            if (!Array.isArray(signalData)) {
                throw new Error('Expected data to be an array');
            }

            values = signalData.map(entry => entry.value);
            labels = signalData.map(entry => moment(entry.timestamp).format('YYYY-MM-DDTHH:mm:ss'));

            values = applyScaling(currentSignal, values);
        }

        const yMax = yAxisMaxMapping[currentSignal] || 100;

        if (!myChart) {
            createChart(labels, values, yMax);
        } else {
            myChart.data.labels = labels;
            myChart.data.datasets[0].data = values;
            myChart.data.datasets[0].label = `${currentSignal} Data`;
            myChart.options.scales.y.max = yMax;
            myChart.update();
        }

        // Update active-signal class on data-row elements
        document.querySelectorAll('.data-row.clickable').forEach(row => {
            row.classList.remove('active-signal');
            if (row.dataset.signal.toLowerCase() === currentSignal.toLowerCase()) {
                row.classList.add('active-signal');
            }
        });
    } catch (error) {
        console.error("Error updating the graph:", error);
    }
}

/**
 * Switches the current signal and updates the graph.
 * @param {string} signal - The signal to switch to.
 */
function switchSignal(signal) {
    currentSignal = signal;
    updateGraph(); 
}

/**
 * Sets up event listeners for clickable data-row elements to switch signals.
 */
function setupSignalSwitching() {
    const clickableRows = document.querySelectorAll('.data-row.clickable');

    clickableRows.forEach(row => {
        row.addEventListener('click', () => {
            const signal = row.dataset.signal;
            let correctedSignal = signal;

            if (signal.toLowerCase() === 'theoflow') {
                correctedSignal = 'TheoFlow';
            } else if (signal.toLowerCase() === 'efficiency') {
                correctedSignal = 'Efficiency';
            } else {
                correctedSignal = signal.toUpperCase();
            }

            switchSignal(correctedSignal);
        });

        // Accessibility: Handle Enter and Space key presses
        row.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                row.click();
            }
        });
    });
}

/**
 * Sets up event listeners for signal switching after DOM content is loaded.
 */
document.addEventListener('DOMContentLoaded', () => {
    // setupSignalSwitching();
    // switchSignal('S1'); // Initialize with 'S1'
});

/**
 * Applies scaling factors to signal data based on the signal type.
 * @param {string} signal - The signal type.
 * @param {Array} values - The raw data values.
 * @returns {Array} - The scaled data values.
 */
function applyScaling(signal, values) {
    switch (signal) {
        case 'S1':
            return values.map(value => value);
        case 'T1':
        case 'T3':
            return values.map(value => value * 0.1);
        case 'F1':
        case 'F2':
        case 'F3':
            return values.map(value => value * 0.01);
        case 'P1':
        case 'P2':
        case 'P3':
        case 'P4':
        case 'P5':
            return values.map(value => value);
        case 'TheoFlow': 
            return values.map(value => value);
        case 'Efficiency':
            return values.map(value => value);
        default:
            return values;
    }
}

/**
 * Fetches the current mode from the server and handles mode transitions.
 */
async function fetchMode() {
    const modeTitle = document.getElementById('mode-title');
    try {
        const response = await fetch('/get_mode');
        if (!response.ok) {
            modeTitle.textContent = "Mode: Unknown - No Connection";
            throw new Error("Network response was not ok");
        }
        
        const data = await response.json();

        if (data.error) {
            modeTitle.textContent = "Mode: Unknown - No Connection";
            throw new Error(data.error || "Failed to fetch mode");
        }

        let currentMode;
        if (data.signalPB4 === 1) {
            currentMode = "Manual";
        } else if (data.signalPB4 === 0) {
            currentMode = "Automatic";
        } else {
            currentMode = "Unknown";
        }

        modeTitle.textContent = `Mode: ${currentMode}`;

        // Retrieve previousMode and hasPromptedForAutomatic from sessionStorage
        previousMode = sessionStorage.getItem('previousMode') || null;
        hasPromptedForAutomatic = sessionStorage.getItem('hasPromptedForAutomatic') === 'true';

        // Only show the clear-data modal if the user is an admin
        if (sessionStorage.getItem('isAdmin') === 'true' && 
            currentMode === "Automatic" &&
            previousMode !== "Automatic" &&
            !hasPromptedForAutomatic) {
                hasPromptedForAutomatic = true; // Set the flag to prevent further prompts

            // Show the Bootstrap modal
            $('#clear-data-modal').modal('show');

            // Handle Confirm Button Click
            $('#confirm-clear-button').off('click').on('click', async () => {
                $('#clear-data-modal').modal('hide');
                try {
                    const clearResponse = await fetch('/clear_data_table', { method: 'POST' });
                    const clearData = await clearResponse.json();
                    if (clearData.status === 'success') {
                        showSuccess('Data table cleared successfully. The heading is still intact.');
                        // Optionally, refresh the page or update the UI as needed
                        location.reload();
                    } else {
                        showError("Failed to clear the data table: " + clearData.message);
                    }
                } catch (error) {
                    console.error('Error clearing data table:', error);
                    showError('An error occurred while clearing the data table.');
                }
            });

            // Handle Cancel Button Click
            $('#cancel-clear-button').off('click').on('click', () => {
                console.log("User chose to keep existing data in the data table.");
                // Continue appending to the existing data as usual
            });

            // Save the updated flag to sessionStorage
            sessionStorage.setItem('hasPromptedForAutomatic', 'true');
        }

        // Reset the flag if mode changes away from Automatic
        if (currentMode !== "Automatic") {
            hasPromptedForAutomatic = false;
            sessionStorage.setItem('hasPromptedForAutomatic', 'false');
        }

        // Update previousMode and save it to sessionStorage
        sessionStorage.setItem('previousMode', currentMode);
        previousMode = currentMode;

    } catch(error) {
        console.error("Error fetching the mode:", error)
        modeTitle.textContent = "Mode: Unknown - No Connection"
    }
}

/**
 * Fetches CSV data from the server and populates the data table.
 */
async function fetchCSVData() {
    try {
        const response = await fetch('/get_csv_data');

        if (!response.ok) {
            if (response.status === 404) {
                console.warn("CSV file not found. It may not have been generated yet.");
            } else {
                console.error(`Error: ${response.statusText}`);
            }
            return;
        }

        const result = await response.json();

        if (!result.data || Object.keys(result.data).length === 0) {
            console.warn("No CSV data available yet.");
            return;
        }

        csvGenerated = true;

        const data = Object.values(result.data).slice(-20).reverse();
        const tableBody = document.getElementById('data-table');
        tableBody.innerHTML = '';

        const columns = [
            "Date", "Time", "S1", "SP", "TP", "Cycle", "Cycle Timer", "LCSetpoint", "LC Regulate", "Step", "F1", "F2", "F3", "T1", "T3", "P1", "P2", "P3", "P4", "P5"
        ];

        data.forEach(row => {
            const tr = document.createElement('tr');

            columns.forEach(column => {
                const td = document.createElement('td');
                switch(column) {
                    case "TP":
                        td.textContent = (row[column] / 10.23).toFixed(2);
                        break;
                    case "Cycle Timer":
                        td.textContent = (row[column] / 100).toFixed(2);
                        break;
                    case "F1":
                    case "F2":
                    case "F3":
                        td.textContent = (row[column] * 0.01).toFixed(2);
                        break;
                    case "T1":
                    case "T3":
                        td.textContent = (row[column] * 0.1).toFixed(1);
                        break;
                    default:
                        td.textContent = row[column] || ''; 
                }
                tr.appendChild(td);
            });

            const theoFlow = (row["S1"] * inputFactor) / 231;
            const f1 = (row["F1"]) * 0.01;
            const efficiency = theoFlow !== 0 ? ((f1 / theoFlow) * 100) : 0;

            const theoFlowTd = document.createElement('td');
            theoFlowTd.textContent = theoFlow.toFixed(2);
            tr.appendChild(theoFlowTd);

            const efficiencyTd = document.createElement('td');
            efficiencyTd.textContent = efficiency.toFixed(2);
            tr.appendChild(efficiencyTd);

            tableBody.appendChild(tr);
        });
    } catch (error) {
        console.error("Error fetching CSV data:", error);
    }
}

/**
 * Loads header data from the server and populates the header fields.
 */
async function loadHeaderData() {
    try {
        const response = await fetch('/get_header_data');
        if (!response.ok) {
            throw new Error("Network response was not ok");
        }

        const data = await response.json();

        const programNameElem = document.getElementById('headerProgramName');
        if (programNameElem) programNameElem.value = data.programName || "N/A";

        const descriptionElem = document.getElementById('headerDescription');
        if (descriptionElem) descriptionElem.value = data.description || "N/A";

        const compsetElem = document.getElementById('headerCompSet');
        if (compsetElem) compsetElem.value = data.compSet || "N/A";

        const inputFactorElem = document.getElementById('headerInputFactor');
        if (inputFactorElem) {
            inputFactorElem.value = data.inputFactor || "N/A";

            // Parse inputFactor as float
            const parsedInputFactor = parseFloat(data.inputFactor);
            if (isNaN(parsedInputFactor)) {
                console.error("Failed to parse InputFactor:", data.inputFactor);
            } else {
                inputFactor = parsedInputFactor;
            }
        } else {
            console.warn("headerInputFactor element not found")
        }

        const serialNumberElem = document.getElementById('headerSerialNumber');
        if (serialNumberElem) serialNumberElem.value = data.serialNumber || "N/A";

        const employeeIdElem = document.getElementById('headerEmployeeId');
        if (employeeIdElem) employeeIdElem.value = data.employeeId || "N/A";

        const customerIdElem = document.getElementById('headerCustomerId');
        if (customerIdElem)  customerIdElem.value = data.customerId || "N/A";

        const inputFactorTypeElem = document.getElementById('headerInputFactorType');
        if (inputFactorTypeElem) inputFactorTypeElem.value = data.inputFactorType || "cu/in";
    } catch (error) {
        console.error("Error loading header data:", error);
    }
}

/**
 * Checks the trending status from the live data.
 */
async function checkTrendingStatus() {
    try {
        const response = await fetch('/get_live_data');
        const data = await response.json();

        if (data.error) {
            console.error("Error fetching live data:", data.error);
            return;
        }

        if (data.trending === 1) {
            csvGenerated = true;
        } else {
            csvGenerated = false;
        }
    } catch (error) {
        console.error("Error checking trending status:", error);
    }
}

setInterval(fetchCSVData, 5000);
setInterval(checkTrendingStatus, 5000);

/**
 * Displays an error message in the export-error alert.
 * @param {string} message - The error message to display.
 */
function showError(message) {
    const toast = $('#error-toast');
    if (toast.length) {
        toast.find('.toast-body').text(message);
        toast.toast('show');
    } else {
        console.warn("error-toast element not found");
    }
    // const errorElement = document.getElementById('export-error');
    // const errorMessage = document.getElementById('error-message');
    // errorMessage.textContent = message;
    // errorElement.style.display = 'block';
}

/**
 * Dismisses the export-error alert.
 */
function dismissError() {
    const errorElement = document.getElementById('export-error');
    errorElement.style.display = 'none';
}

function showSuccess(message) {
    const toast = $('#success-toast');
    if (toast.length) {
        toast.find('.toast-body').text(message);
        toast.toast('show');
    } else {
        console.warn("success-toast element not found")
    }
    
}

// function initVideoPanning() {
//     const overlay = document.getElementById('videoPanOverlay');
//     const iframe = document.getElementById('videoPanIframe');

//     if (!overlay || !iframe) {
//         console.warn("overlay or iframe not found")
//         return;
//     }

//     let isDragging = false;
//     let startX = 0, startY = 0;
//     let currentX = 0, currentY = 0;

//     // Mouse down: start drag
//     overlay.addEventListener('mousedown', function(e) {
//         isDragging = true;
//         overlay.style.cursor = 'grabbing';
//         startX = e.clientX - currentX;
//         startY = e.clientY - currentY;
//     });

//     // Mouse move: if dragging, update position
//     overlay.addEventListener('mousemove', function(e) {
//         if (!isDragging) return;
//         currentX = e.clientX - startX;
//         currentY = e.clientY - startY;

//         iframe.style.transform = `translate(${currentX}px, ${currentY}px)`;
//     });

//     // Mouse up: stop drag
//     overlay.addEventListener('mouseup', function() {
//         isDragging = false;
//         overlay.style.cursor = 'grab';
//     });

//     // If the mouse leaves the container, stop dragging
//     overlay.addEventListener('mouseleave', function() {
//         isDragging = false;
//         overlay.style.cursor = 'grab';
//     });
// }