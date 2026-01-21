// State management
let currentPlan = {
    gpx_filename: null,
    checkpoint_distances: [],
    segments: null,
    summary: null,
    elevation_profile: null
};

let elevationChart = null;

// DOM Elements
const gpxFileInput = document.getElementById('gpx-file');
const fileNameDisplay = document.getElementById('file-name');
const gpxInfoBox = document.getElementById('gpx-info');
const numCheckpointsInput = document.getElementById('num-checkpoints');
const checkpointDistancesContainer = document.getElementById('checkpoint-distances');
const calculateBtn = document.getElementById('calculate-btn');
const saveBtn = document.getElementById('save-btn');
const loadBtn = document.getElementById('load-btn');
const exportBtn = document.getElementById('export-btn');
const resultsContainer = document.getElementById('results-container');
const noResults = document.getElementById('no-results');

// Modal elements
const saveModal = document.getElementById('save-modal');
const loadModal = document.getElementById('load-modal');
const saveConfirmBtn = document.getElementById('save-confirm-btn');
const saveCancelBtn = document.getElementById('save-cancel-btn');
const loadCancelBtn = document.getElementById('load-cancel-btn');
const planNameInput = document.getElementById('plan-name');
const plansList = document.getElementById('plans-list');
const clearBtn = document.getElementById('clear-btn');

// Event Listeners
gpxFileInput.addEventListener('change', handleGPXUpload);
numCheckpointsInput.addEventListener('change', generateCheckpointInputs);
calculateBtn.addEventListener('click', calculateRacePlan);
saveBtn.addEventListener('click', showSaveModal);
loadBtn.addEventListener('click', showLoadModal);
exportBtn.addEventListener('click', exportToCSV);
clearBtn.addEventListener('click', clearAll);
saveConfirmBtn.addEventListener('click', savePlan);
saveCancelBtn.addEventListener('click', () => hideModal(saveModal));
loadCancelBtn.addEventListener('click', () => hideModal(loadModal));

// Add real-time calculation on input changes
document.querySelectorAll('input, select').forEach(input => {
    if (input.id !== 'gpx-file' && input.id !== 'plan-name') {
        input.addEventListener('change', () => {
            if (currentPlan.gpx_filename) {
                calculateRacePlan();
            }
        });
    }
});

// Initialize
generateCheckpointInputs();

// Functions
function renderElevationChart(elevationProfile, segments) {
    const ctx = document.getElementById('elevation-chart');
    
    // Destroy existing chart
    if (elevationChart) {
        elevationChart.destroy();
    }
    
    // Prepare checkpoint markers
    const checkpointDistances = segments.map((seg, idx) => {
        // Get cumulative distance at end of each segment
        const cumDist = segments.slice(0, idx + 1).reduce((sum, s) => sum + s.distance, 0);
        return {
            distance: cumDist,
            label: seg.to
        };
    });
    
    // Create gradient
    const gradient = ctx.getContext('2d').createLinearGradient(0, 0, 0, 300);
    gradient.addColorStop(0, 'rgba(37, 99, 235, 0.5)');
    gradient.addColorStop(1, 'rgba(37, 99, 235, 0.1)');
    
    elevationChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: elevationProfile.map(p => p.distance.toFixed(1)),
            datasets: [{
                label: 'Elevation (m)',
                data: elevationProfile.map(p => p.elevation),
                borderColor: 'rgb(37, 99, 235)',
                backgroundColor: gradient,
                fill: true,
                tension: 0.4,
                pointRadius: 0,
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        title: (context) => `Distance: ${context[0].label} km`,
                        label: (context) => `Elevation: ${context.parsed.y.toFixed(0)} m`
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Distance (km)',
                        font: {
                            size: 12,
                            weight: 'bold'
                        }
                    },
                    ticks: {
                        maxTicksLimit: 15,
                        callback: function(value, index) {
                            // Show every nth tick based on data size
                            const step = Math.ceil(elevationProfile.length / 15);
                            return index % step === 0 ? this.getLabelForValue(value) : '';
                        }
                    },
                    grid: {
                        display: true,
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Elevation (m)',
                        font: {
                            size: 12,
                            weight: 'bold'
                        }
                    },
                    grid: {
                        display: true,
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
}

function clearAll() {
    if (!confirm('Are you sure you want to clear all data and start again?')) {
        return;
    }
    
    // Reset state
    currentPlan = {
        gpx_filename: null,
        checkpoint_distances: [],
        segments: null,
        summary: null,
        elevation_profile: null
    };
    
    // Destroy chart
    if (elevationChart) {
        elevationChart.destroy();
        elevationChart = null;
    }
    
    // Reset file input
    gpxFileInput.value = '';
    fileNameDisplay.textContent = 'Choose GPX file...';
    gpxInfoBox.style.display = 'none';
    
    // Reset all inputs to defaults
    document.getElementById('num-checkpoints').value = 3;
    document.getElementById('avg-cp-time').value = 5;
    document.getElementById('z2-pace-min').value = 6;
    document.getElementById('z2-pace-sec').value = 30;
    document.getElementById('elev-gain-factor').value = 6.0;
    document.getElementById('carbs-per-hour').value = 60;
    document.getElementById('water-per-hour').value = 500;
    document.getElementById('race-start-time').value = '';
    
    // Regenerate checkpoint inputs
    generateCheckpointInputs();
    
    // Hide results
    resultsContainer.style.display = 'none';
    noResults.style.display = 'block';
    
    // Disable buttons
    saveBtn.disabled = true;
    exportBtn.disabled = true;
}

async function handleGPXUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    fileNameDisplay.textContent = file.name;
    
    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/upload-gpx', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            currentPlan.gpx_filename = data.filename;
            
            gpxInfoBox.innerHTML = `
                <strong>Route Loaded:</strong><br>
                Distance: ${data.total_distance} km (${data.total_distance_miles} miles)<br>
                Elevation Gain: +${data.total_elev_gain} m / -${data.total_elev_loss} m<br>
                Trackpoints: ${data.num_trackpoints}
            `;
            gpxInfoBox.style.display = 'block';

            // Auto-calculate if checkpoints are already set
            if (currentPlan.checkpoint_distances.length > 0) {
                calculateRacePlan();
            }
        } else {
            alert('Error: ' + data.error);
        }
    } catch (error) {
        alert('Error uploading GPX file: ' + error.message);
    }
}

function generateCheckpointInputs() {
    const numCheckpoints = parseInt(numCheckpointsInput.value) || 0;
    checkpointDistancesContainer.innerHTML = '';

    for (let i = 0; i < numCheckpoints; i++) {
        const div = document.createElement('div');
        div.className = 'checkpoint-input';
        div.innerHTML = `
            <label>Checkpoint ${i + 1} Distance (km):</label>
            <input type="number" 
                   class="checkpoint-distance" 
                   data-index="${i}" 
                   step="0.1" 
                   min="0"
                   value="${currentPlan.checkpoint_distances[i] || ''}"
                   placeholder="e.g., 25.0" />
        `;
        checkpointDistancesContainer.appendChild(div);
    }

    // Add event listeners for real-time updates
    document.querySelectorAll('.checkpoint-distance').forEach(input => {
        input.addEventListener('change', () => {
            if (currentPlan.gpx_filename) {
                calculateRacePlan();
            }
        });
    });
}

async function calculateRacePlan() {
    if (!currentPlan.gpx_filename) {
        alert('Please upload a GPX file first');
        return;
    }

    // Gather checkpoint distances
    const checkpointInputs = document.querySelectorAll('.checkpoint-distance');
    currentPlan.checkpoint_distances = Array.from(checkpointInputs)
        .map(input => parseFloat(input.value))
        .filter(val => !isNaN(val));

    // Gather other inputs
    const avgCpTime = parseFloat(document.getElementById('avg-cp-time').value) || 5;
    const z2PaceMin = parseFloat(document.getElementById('z2-pace-min').value) || 6;
    const z2PaceSec = parseFloat(document.getElementById('z2-pace-sec').value) || 30;
    const z2Pace = z2PaceMin + z2PaceSec / 60;
    const elevGainFactor = parseFloat(document.getElementById('elev-gain-factor').value) || 6.0;
    const carbsPerHour = parseFloat(document.getElementById('carbs-per-hour').value) || 60;
    const waterPerHour = parseFloat(document.getElementById('water-per-hour').value) || 500;
    const raceStartTime = document.getElementById('race-start-time').value || null;

    const requestData = {
        gpx_filename: currentPlan.gpx_filename,
        checkpoint_distances: currentPlan.checkpoint_distances,
        avg_cp_time: avgCpTime,
        z2_pace: z2Pace,
        elev_gain_factor: elevGainFactor,
        carbs_per_hour: carbsPerHour,
        water_per_hour: waterPerHour,
        race_start_time: raceStartTime
    };

    try {
        const response = await fetch('/api/calculate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });

        const data = await response.json();

        if (response.ok) {
            currentPlan.segments = data.segments;
            currentPlan.summary = data.summary;
            currentPlan.race_start_time = raceStartTime;
            displayResults(data);
            saveBtn.disabled = false;
            exportBtn.disabled = false;
        } else {
            alert('Error: ' + data.error);
        }
    } catch (error) {
        alert('Error calculating race plan: ' + error.message);
    }
}

function displayResults(data) {
    const { segments, summary, elevation_profile } = data;

    // Store elevation profile
    currentPlan.elevation_profile = elevation_profile;
    
    // Render elevation chart if profile exists
    if (elevation_profile && elevation_profile.length > 0) {
        renderElevationChart(elevation_profile, segments);
    }

    // Update summary cards
    document.getElementById('summary-distance').textContent = `${summary.total_distance} km`;
    document.getElementById('summary-moving-time').textContent = summary.total_moving_time_str;
    document.getElementById('summary-total-time').textContent = summary.total_race_time_str;
    document.getElementById('summary-elev-gain').textContent = `${summary.total_elev_gain} m`;
    document.getElementById('summary-carbs').textContent = `${summary.total_carbs} g`;
    document.getElementById('summary-water').textContent = `${summary.total_water} L`;

    // Update segments table
    const tbody = document.getElementById('segments-tbody');
    tbody.innerHTML = '';

    const hasTimeOfDay = segments.some(seg => seg.time_of_day !== null);
    const timeOfDayCols = document.querySelectorAll('.time-of-day-col');
    timeOfDayCols.forEach(col => {
        col.style.display = hasTimeOfDay ? 'table-cell' : 'none';
    });

    segments.forEach(seg => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><strong>${seg.from} → ${seg.to}</strong></td>
            <td>${seg.distance}</td>
            <td>+${seg.elev_gain}/-${seg.elev_loss}</td>
            <td>${seg.net_elev > 0 ? '+' : ''}${seg.net_elev}</td>
            <td>${seg.elev_pace_str}</td>
            <td>${seg.fatigue_str}</td>
            <td><strong>${seg.pace_str}</strong></td>
            <td>${seg.segment_time_str}</td>
            <td>${seg.target_carbs}</td>
            <td>${seg.target_water}</td>
            <td><strong>${seg.cumulative_time_str}</strong></td>
            <td class="time-of-day-col" style="display: ${hasTimeOfDay ? 'table-cell' : 'none'}">
                ${seg.time_of_day || '--'}
            </td>
        `;
        tbody.appendChild(row);
    });

    // Show results
    noResults.style.display = 'none';
    resultsContainer.style.display = 'block';
}

function showSaveModal() {
    if (!currentPlan.segments) {
        alert('Please calculate a race plan first');
        return;
    }
    
    // Generate default name
    const now = new Date();
    const defaultName = `race_plan_${now.getFullYear()}${(now.getMonth()+1).toString().padStart(2,'0')}${now.getDate().toString().padStart(2,'0')}`;
    planNameInput.value = defaultName;
    
    saveModal.classList.add('active');
}

function showLoadModal() {
    loadModal.classList.add('active');
    loadSavedPlans();
}

function hideModal(modal) {
    modal.classList.remove('active');
}

async function savePlan() {
    const planName = planNameInput.value.trim();
    
    if (!planName) {
        alert('Please enter a plan name');
        return;
    }

    if (!currentPlan.segments) {
        alert('No race plan to save');
        return;
    }

    const saveData = {
        plan_name: planName,
        gpx_filename: currentPlan.gpx_filename,
        checkpoint_distances: currentPlan.checkpoint_distances,
        avg_cp_time: parseFloat(document.getElementById('avg-cp-time').value),
        z2_pace: parseFloat(document.getElementById('z2-pace-min').value) + parseFloat(document.getElementById('z2-pace-sec').value) / 60,
        elev_gain_factor: parseFloat(document.getElementById('elev-gain-factor').value),
        carbs_per_hour: parseFloat(document.getElementById('carbs-per-hour').value),
        water_per_hour: parseFloat(document.getElementById('water-per-hour').value),
        race_start_time: document.getElementById('race-start-time').value || null,
        segments: currentPlan.segments,
        summary: currentPlan.summary,
        elevation_profile: currentPlan.elevation_profile
    };

    try {
        const response = await fetch('/api/save-plan', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(saveData)
        });

        const data = await response.json();

        if (response.ok) {
            alert('Plan saved successfully!');
            hideModal(saveModal);
        } else {
            alert('Error saving plan: ' + data.error);
        }
    } catch (error) {
        alert('Error saving plan: ' + error.message);
    }
}

async function loadSavedPlans() {
    try {
        const response = await fetch('/api/list-plans');
        const data = await response.json();

        if (response.ok) {
            plansList.innerHTML = '';
            
            if (data.plans.length === 0) {
                plansList.innerHTML = '<p style="text-align: center; color: #64748b;">No saved plans found</p>';
                return;
            }

            data.plans.forEach(plan => {
                const div = document.createElement('div');
                div.className = 'plan-item';
                div.innerHTML = `
                    <div class="plan-info">
                        <div class="plan-name">${plan.name}</div>
                        <div class="plan-date">${plan.modified}</div>
                    </div>
                    <button class="plan-delete" data-filename="${plan.filename}">Delete</button>
                `;
                
                div.querySelector('.plan-info').addEventListener('click', () => loadPlan(plan.filename));
                div.querySelector('.plan-delete').addEventListener('click', (e) => {
                    e.stopPropagation();
                    deletePlan(plan.filename);
                });
                
                plansList.appendChild(div);
            });
        } else {
            alert('Error loading plans: ' + data.error);
        }
    } catch (error) {
        alert('Error loading plans: ' + error.message);
    }
}

async function loadPlan(filename) {
    try {
        const response = await fetch(`/api/load-plan/${filename}`);
        const data = await response.json();

        if (response.ok) {
            // Load plan data into form
            currentPlan.gpx_filename = data.gpx_filename;
            currentPlan.checkpoint_distances = data.checkpoint_distances || [];
            
            document.getElementById('num-checkpoints').value = currentPlan.checkpoint_distances.length;
            document.getElementById('avg-cp-time').value = data.avg_cp_time || 5;
            
            const z2Pace = data.z2_pace || 6.5;
            document.getElementById('z2-pace-min').value = Math.floor(z2Pace);
            document.getElementById('z2-pace-sec').value = Math.round((z2Pace % 1) * 60);
            
            document.getElementById('elev-gain-factor').value = data.elev_gain_factor || 6.0;
            document.getElementById('carbs-per-hour').value = data.carbs_per_hour || 60;
            document.getElementById('water-per-hour').value = data.water_per_hour || 500;
            document.getElementById('race-start-time').value = data.race_start_time || '';

            // Generate checkpoint inputs and populate
            generateCheckpointInputs();

            // Load results if available
            if (data.segments && data.summary) {
                currentPlan.segments = data.segments;
                currentPlan.summary = data.summary;
                currentPlan.race_start_time = data.race_start_time;
                currentPlan.elevation_profile = data.elevation_profile || null;
                
                // If no elevation profile, recalculate to get it
                if (!currentPlan.elevation_profile) {
                    calculateRacePlan();
                } else {
                    displayResults(data);
                }
                
                saveBtn.disabled = false;
                exportBtn.disabled = false;
            }

            hideModal(loadModal);
            alert('Plan loaded successfully!');
        } else {
            alert('Error loading plan: ' + data.error);
        }
    } catch (error) {
        alert('Error loading plan: ' + error.message);
    }
}

async function deletePlan(filename) {
    if (!confirm('Are you sure you want to delete this plan?')) {
        return;
    }

    try {
        const response = await fetch(`/api/delete-plan/${filename}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (response.ok) {
            loadSavedPlans(); // Refresh list
        } else {
            alert('Error deleting plan: ' + data.error);
        }
    } catch (error) {
        alert('Error deleting plan: ' + error.message);
    }
}

async function exportToCSV() {
    if (!currentPlan.segments) {
        alert('Please calculate a race plan first');
        return;
    }

    const exportData = {
        segments: currentPlan.segments,
        summary: currentPlan.summary,
        race_start_time: currentPlan.race_start_time
    };

    try {
        const response = await fetch('/api/export-csv', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(exportData)
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `race_plan_${new Date().getTime()}.csv`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } else {
            const data = await response.json();
            alert('Error exporting CSV: ' + data.error);
        }
    } catch (error) {
        alert('Error exporting CSV: ' + error.message);
    }
}
