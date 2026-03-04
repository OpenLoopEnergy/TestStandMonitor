document.addEventListener('DOMContentLoaded', async () => {
    try {
        const response = await fetch('/get_dvc_values');
        if (!response.ok) {
            throw new Error('Failed to fetch DVC values');
        }
        const dvcValues = await response.json();

        // Update the form fields and the DVC span elements with the fetched values
        Object.keys(dvcValues).forEach(key => {
            if (dvcValues[key] !== null) {
                document.getElementById(key).value = dvcValues[key];
                document.getElementById(`dvc-${key}`).textContent = dvcValues[key];
            }
        });
    } catch (error) {
        console.error('Error loading DVC values:', error);
    }
});

function start() {
    console.log('Start button clicked');
}

function stop() {
    console.log('Stop button clicked');
}

function toggleEmergencyStop() {
    const emergencyButton = document.querySelector('.btn-emergency');
    emergencyButton.classList.toggle('active');

    if (emergencyButton.classList.contains('active')) {
        console.log('Emergency Stop Engaged');
        // additional logic will go here
    } else {
        console.log('Emergency Stop Disengaged')
        // additional logic will go here
    }
}

function saveChanges() {
    const form = document.getElementById('ee-memory-form');
    const formData = new FormData(form);
    let allFilled = true;

    formData.forEach((value, key) => {
        if (!value) {
            allFilled = false;
            document.getElementById(key).classList.add('is-invalid');
        } else {
            document.getElementById(key).classList.remove('is-invalid');
        }
    });

    if (!allFilled) {
        alert('Please fill out all fields.');
        return;
    }

    const data = {};
    formData.forEach((value, key) => {
        data[key] = Number(value);
    });

    // Send form data to the server via POST
    fetch('/save_ee_memory', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.status === 'success') {
            alert('EE-Memory values sent successfully over CAN Bus.');
        } else {
            alert('Error sending EE-Memory values: ' + result.message);
        }
    })
    .catch(error => {
        console.error('Error sending EE-Memory values:', error);
    });
}
