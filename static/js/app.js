// Constants
const MAX_CHECKPOINTS = 30;

// Helper to convert a string to Unicode bold (for tooltips)
function toUnicodeBold(str) {
    const map = {
        A: '𝗔', B: '𝗕', C: '𝗖', D: '𝗗', E: '𝗘', F: '𝗙', G: '𝗚', H: '𝗛', I: '𝗜', J: '𝗝',
        K: '𝗞', L: '𝗟', M: '𝗠', N: '𝗡', O: '𝗢', P: '𝗣', Q: '𝗤', R: '𝗥', S: '𝗦', T: '𝗧',
        U: '𝗨', V: '𝗩', W: '𝗪', X: '𝗫', Y: '𝗬', Z: '𝗭',
        a: '𝗮', b: '𝗯', c: '𝗰', d: '𝗱', e: '𝗲', f: '𝗳', g: '𝗴', h: '𝗵', i: '𝗶', j: '𝗷',
        k: '𝗸', l: '𝗹', m: '𝗺', n: '𝗻', o: '𝗼', p: '𝗽', q: '𝗾', r: '𝗿', s: '𝘀', t: '𝘁',
        u: '𝘂', v: '𝘃', w: '𝘄', x: '𝘅', y: '𝘆', z: '𝘇',
        '-': '⟶'
    };
    return str.split('').map(c => map[c] || c).join('');
}

// Helper to format timestamps in local timezone
// Accepts timestamps in various formats and converts to local timezone display
function formatTimestampToLocal(timestampStr) {
    if (!timestampStr) return '';
    
    // Handle different timestamp formats from backend:
    // 1. ISO format from Supabase: "2024-01-15T14:30:45+00:00" or "2024-01-15T14:30:45.123Z"
    // 2. Space-separated format: "2024-01-15 14:30:45" (assumed UTC)
    
    let date;
    
    // Try parsing as ISO format first (includes timezone info)
    if (timestampStr.includes('T')) {
        date = new Date(timestampStr);
    } else {
        // Space-separated format - assume UTC, convert to ISO format with 'Z'
        date = new Date(timestampStr.replace(' ', 'T') + 'Z');
    }
    
    // Check if date is valid
    if (isNaN(date.getTime())) {
        console.warn('Invalid timestamp:', timestampStr);
        return timestampStr; // Return original if parsing fails
    }
    
    // Format to local timezone: YYYY-MM-DD HH:MM:SS
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');
    
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
}

// Helper to update the race plan title
function updateRacePlanTitle(planName = null) {
    if (planName) {
        racePlanTitle.textContent = `Race Plan: ${planName}`;
    } else {
        racePlanTitle.textContent = 'Race Plan';
    }
}

// State management
let currentPlan = {
    gpx_filename: null,
    checkpoint_distances: [],
    checkpoint_dropbags: [],  // Track which checkpoints have dropbags
    segment_terrain_types: [],
    segments: null,
    summary: null,
    elevation_profile: null,
    dropbag_contents: null,  // Calculated dropbag contents for each CP
    loadedFilename: null,  // Track the currently loaded plan filename
    loadedSource: null,  // Track the source of the loaded plan ('local' or 'supabase')
    planName: null,  // Track the currently loaded plan name for UI display
    total_distance: null,  // Total distance of the route
    is_known_race: false,  // Whether this is a known race
    race_start_time: null,  // Race start time for time-of-day calculations
    pacing_mode: 'base_pace'  // 'base_pace' or 'target_time'
};

let elevationChart = null;

// DOM Elements
const gpxFileInput = document.getElementById('gpx-file');
const fileNameDisplay = document.getElementById('file-name');
const gpxInfoBox = document.getElementById('gpx-info');
const numCheckpointsInput = document.getElementById('num-checkpoints');
const checkpointDistancesContainer = document.getElementById('checkpoint-distances');
const checkpointCounter = document.getElementById('checkpoint-counter');
const calculateBtn = document.getElementById('calculate-btn');
const saveBtn = document.getElementById('save-btn');
const loadBtn = document.getElementById('load-btn');
const exportBtn = document.getElementById('export-btn');
const resultsContainer = document.getElementById('results-container');
const noResults = document.getElementById('no-results');
const racePlanTitle = document.getElementById('race-plan-title');

// Modal elements
const saveModal = document.getElementById('save-modal');
const loadModal = document.getElementById('load-modal');
const exportImportModal = document.getElementById('export-import-modal');
const saveConfirmBtn = document.getElementById('save-confirm-btn');
const saveAsBtn = document.getElementById('save-as-btn');
const saveCancelBtn = document.getElementById('save-cancel-btn');
const loadCancelBtn = document.getElementById('load-cancel-btn');
const importUnownedPlansBtn = document.getElementById('import-unowned-plans-btn');
const exportImportCancelBtn = document.getElementById('export-import-cancel-btn');
const planNameInput = document.getElementById('plan-name');
const plansList = document.getElementById('plans-list');
const clearBtn = document.getElementById('clear-btn');
const fatigueEnabledInput = document.getElementById('fatigue-enabled');
const fitnessLevelInput = document.getElementById('fitness-level');
const terrainEnabledInput = document.getElementById('terrain-enabled');
const terrainSkillContainer = document.getElementById('terrain-skill-container');
const terrainDifficultiesContainer = document.getElementById('terrain-difficulties');
const skillLevelInput = document.getElementById('skill-level');
const defaultTerrainTypeInput = document.getElementById('default-terrain-type');
const exportImportBtn = document.getElementById('export-import-btn');
const exportPlanBtn = document.getElementById('export-plan-btn');
const importPlanBtn = document.getElementById('import-plan-btn');
const importPlanFileInput = document.getElementById('import-plan-file-input');

// Known Race modal elements
const loadKnownRaceBtn = document.getElementById('load-known-race-btn');
const knownRaceModal = document.getElementById('known-race-modal');
const knownRaceSearch = document.getElementById('known-race-search');
const knownRacesList = document.getElementById('known-races-list');
const knownRaceCancelBtn = document.getElementById('known-race-cancel-btn');

// Pacing mode elements
const pacingModeBaseRadio = document.getElementById('pacing-mode-base');
const pacingModeTargetRadio = document.getElementById('pacing-mode-target');
const basePaceInputs = document.getElementById('base-pace-inputs');
const targetTimeInputs = document.getElementById('target-time-inputs');
const targetTimeHoursInput = document.getElementById('target-time-hours');
const targetTimeMinutesInput = document.getElementById('target-time-minutes');
const targetTimeSecondsInput = document.getElementById('target-time-seconds');
const targetTimeWarning = document.getElementById('target-time-warning');

// Event Listeners
gpxFileInput.addEventListener('change', handleGPXUpload);
numCheckpointsInput.addEventListener('input', () => {
    let value = parseInt(numCheckpointsInput.value) || 0;
    
    // Enforce maximum limit
    if (value > MAX_CHECKPOINTS) {
        value = MAX_CHECKPOINTS;
        numCheckpointsInput.value = MAX_CHECKPOINTS;
    }
    
    // Update checkpoint counter
    updateCheckpointCounter(value, MAX_CHECKPOINTS);
    
    generateCheckpointInputs();
    validateCheckpointDistances();
});
calculateBtn.addEventListener('click', calculateRacePlan);
saveBtn.addEventListener('click', showSaveModal);
loadBtn.addEventListener('click', showLoadModal);
exportBtn.addEventListener('click', exportToCSV);
clearBtn.addEventListener('click', clearAll);
saveConfirmBtn.addEventListener('click', () => savePlan(false));
saveAsBtn.addEventListener('click', () => savePlan(true));
saveCancelBtn.addEventListener('click', () => hideModal(saveModal));
loadCancelBtn.addEventListener('click', () => hideModal(loadModal));
importUnownedPlansBtn.addEventListener('click', importUnownedPlans);
exportImportBtn.addEventListener('click', showExportImportModal);
exportImportCancelBtn.addEventListener('click', () => hideModal(exportImportModal));
exportPlanBtn.addEventListener('click', exportCurrentPlan);
importPlanBtn.addEventListener('click', () => importPlanFileInput.click());
importPlanFileInput.addEventListener('change', handleImportPlan);

// Known Race listeners
loadKnownRaceBtn.addEventListener('click', showKnownRaceModal);
knownRaceCancelBtn.addEventListener('click', () => hideModal(knownRaceModal));
knownRaceSearch.addEventListener('input', filterKnownRaces);

// Pacing mode listeners
pacingModeBaseRadio.addEventListener('change', handlePacingModeChange);
pacingModeTargetRadio.addEventListener('change', handlePacingModeChange);

// Fatigue checkbox toggles fitness level dropdown
fatigueEnabledInput.addEventListener('change', () => {
    fitnessLevelInput.disabled = !fatigueEnabledInput.checked;
    if (currentPlan.gpx_filename) {
        calculateRacePlan();
    }
});

// Terrain difficulty checkbox toggles terrain difficulty dropdowns
terrainEnabledInput.addEventListener('change', () => {
    terrainSkillContainer.style.display = terrainEnabledInput.checked ? 'block' : 'none';
    if (terrainEnabledInput.checked) {
        generateTerrainDifficultyInputs();
    }
    if (currentPlan.gpx_filename) {
        calculateRacePlan();
    }
});

// Default terrain type applies to all segments
defaultTerrainTypeInput.addEventListener('change', () => {
    const defaultValue = defaultTerrainTypeInput.value;
    if (defaultValue) {
        // Apply to all segment terrain dropdowns
        const terrainInputs = document.querySelectorAll('.segment-terrain-type');
        terrainInputs.forEach(input => {
            input.value = defaultValue;
        });
        
        if (currentPlan.gpx_filename) {
            calculateRacePlan();
        }
    }
});

// Add real-time calculation on input changes
document.querySelectorAll('input, select').forEach(input => {
    if (input.id !== 'gpx-file' && input.id !== 'plan-name' && input.id !== 'default-terrain-type') {
        input.addEventListener('change', () => {
            if (currentPlan.gpx_filename) {
                calculateRacePlan();
            }
        });
    }
});

// Set up input filtering for numeric fields
setupNumericInputFiltering();

// Functions
function setupNumericInputFiltering() {
    // Integer-only fields
    const integerFields = ['num-checkpoints', 'z2-pace-min', 'z2-pace-sec'];
    integerFields.forEach(fieldId => {
        const input = document.getElementById(fieldId);
        if (input) {
            setupIntegerInput(input);
        }
    });
    
    // Decimal-allowed fields
    const decimalFields = ['avg-cp-time', 'carbs-per-hour', 'water-per-hour', 'carbs-per-gel'];
    decimalFields.forEach(fieldId => {
        const input = document.getElementById(fieldId);
        if (input) {
            setupDecimalInput(input);
        }
    });
}

function setupIntegerInput(input) {
    // Prevent non-numeric key presses
    input.addEventListener('keydown', (e) => {
        // Allow: backspace, delete, tab, escape, enter
        if ([46, 8, 9, 27, 13].indexOf(e.keyCode) !== -1 ||
            // Allow: Ctrl+A, Ctrl+C, Ctrl+V, Ctrl+X, Ctrl+Z
            (e.ctrlKey === true && [65, 67, 86, 88, 90].indexOf(e.keyCode) !== -1) ||
            // Allow: home, end, left, right
            (e.keyCode >= 35 && e.keyCode <= 39)) {
            return;
        }
        // Ensure that it is a number and stop the keypress if not
        if ((e.shiftKey || (e.keyCode < 48 || e.keyCode > 57)) && (e.keyCode < 96 || e.keyCode > 105)) {
            e.preventDefault();
        }
    });
    
    // Filter input to integers only
    input.addEventListener('input', (e) => {
        const value = e.target.value.replace(/[^0-9]/g, '');
        e.target.value = value;
    });
}

function setupDecimalInput(input) {
    // Prevent non-numeric key presses (allow decimal point)
    input.addEventListener('keydown', (e) => {
        // Allow: backspace, delete, tab, escape, enter, decimal point
        if ([46, 8, 9, 27, 13, 110, 190].indexOf(e.keyCode) !== -1 ||
            // Allow: Ctrl+A, Ctrl+C, Ctrl+V, Ctrl+X, Ctrl+Z
            (e.ctrlKey === true && [65, 67, 86, 88, 90].indexOf(e.keyCode) !== -1) ||
            // Allow: home, end, left, right
            (e.keyCode >= 35 && e.keyCode <= 39)) {
            return;
        }
        // Ensure that it is a number and stop the keypress if not
        if ((e.shiftKey || (e.keyCode < 48 || e.keyCode > 57)) && (e.keyCode < 96 || e.keyCode > 105)) {
            e.preventDefault();
        }
    });
    
    // Filter input to allow decimals
    input.addEventListener('input', (e) => {
        const value = e.target.value.replace(/[^0-9.]/g, '');
        // Ensure only one decimal point
        const parts = value.split('.');
        if (parts.length > 2) {
            e.target.value = parts[0] + '.' + parts.slice(1).join('');
        } else {
            e.target.value = value;
        }
    });
}

// Functions
function renderElevationChart(elevationProfile, segments) {
    // Check if Chart.js is available
    if (typeof Chart === 'undefined') {
        console.warn('Chart.js not available - elevation chart will not be rendered');
        const chartContainer = document.getElementById('elevation-chart');
        if (chartContainer && chartContainer.parentElement) {
            chartContainer.parentElement.innerHTML = '<p style="text-align: center; padding: 20px; color: #666;">Elevation chart unavailable (Chart.js library not loaded)</p>';
        }
        return;
    }
    
    const ctx = document.getElementById('elevation-chart');
    
    // Destroy existing chart
    if (elevationChart) {
        elevationChart.destroy();
    }
    
    // Prepare checkpoint data with nutrition info
    const checkpointData = [];
    let cumulativeDist = 0;
    
    segments.forEach((seg, idx) => {
        cumulativeDist += seg.distance;
        
        // Skip the finish line (last segment)
        if (idx < segments.length - 1) {
            const cpNumber = idx + 1;
            const distanceToNext = segments[idx + 1].distance;
            const carbsToNext = segments[idx + 1].target_carbs;
            const waterToNext = segments[idx + 1].target_water;
            
            checkpointData.push({
                distance: cumulativeDist,
                cpNumber: cpNumber,
                label: seg.to,
                distanceToNext: distanceToNext,
                carbsToNext: carbsToNext,
                waterToNext: waterToNext,
                timeToNext: segments[idx + 1].segment_time_str
            });
        }
    });
    
    // Create gradient
    const gradient = ctx.getContext('2d').createLinearGradient(0, 0, 0, 300);
    gradient.addColorStop(0, 'rgba(37, 99, 235, 0.5)');
    gradient.addColorStop(1, 'rgba(37, 99, 235, 0.1)');
    
    // Plugin to draw checkpoint lines
    const checkpointLinesPlugin = {
        id: 'checkpointLines',
        afterDatasetsDraw: (chart) => {
            const { ctx, chartArea: { top, bottom, left, right }, scales: { x, y } } = chart;
            
            checkpointData.forEach(cp => {
                // Find the closest index in elevation profile to this checkpoint distance
                let closestIndex = 0;
                let minDiff = Math.abs(elevationProfile[0].distance - cp.distance);
                
                for (let i = 1; i < elevationProfile.length; i++) {
                    const diff = Math.abs(elevationProfile[i].distance - cp.distance);
                    if (diff < minDiff) {
                        minDiff = diff;
                        closestIndex = i;
                    }
                }
                
                // Get pixel position using the index
                const xPos = x.getPixelForValue(closestIndex);
                
                // Draw vertical dotted line
                ctx.save();
                ctx.strokeStyle = 'rgba(239, 68, 68, 0.7)';
                ctx.lineWidth = 2;
                ctx.setLineDash([5, 5]);
                ctx.beginPath();
                ctx.moveTo(xPos, top);
                ctx.lineTo(xPos, bottom);
                ctx.stroke();
                ctx.restore();
                
                // Draw checkpoint label
                ctx.save();
                ctx.fillStyle = 'rgba(239, 68, 68, 0.9)';
                ctx.font = 'bold 11px sans-serif';
                ctx.textAlign = 'center';
                ctx.fillText(cp.label, xPos, top - 5);
                ctx.restore();
            });
        }
    };
    
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
            layout: {
                padding: {
                    top: 20
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        title: (context) => {
                            const distance = parseFloat(context[0].label);
                            // Check if we're near a checkpoint
                            const nearCheckpoint = checkpointData.find(cp => 
                                Math.abs(cp.distance - distance) < 0.5
                            );
                            let titleLines = [];
                            if (nearCheckpoint) {
                                titleLines.push(`${nearCheckpoint.label}`);
                                titleLines.push(`Distance: ${nearCheckpoint.distance.toFixed(1)} km`);
                            } else {
                                titleLines.push(`Distance: ${distance} km`);
                            }
                            return titleLines;
                        },
                        label: (context) => {
                            const distance = parseFloat(context.label);
                            const labels = [`Elevation: ${context.parsed.y.toFixed(0)} m`];
                            // Check if we're near a checkpoint
                            const nearCheckpoint = checkpointData.find(cp => 
                                Math.abs(cp.distance - distance) < 0.5
                            );
                            if (nearCheckpoint) {
                                const timeParts = nearCheckpoint.timeToNext.split(':');
                                const hours = parseInt(timeParts[0]);
                                const mins = parseInt(timeParts[1]);
                                labels.push(`Next CP: ${nearCheckpoint.distanceToNext.toFixed(1)} km / ${hours} hrs, ${mins} mins`);
                                labels.push('');
                                // Find previous and next checkpoint labels for the section
                                let prevLabel = '';
                                let nextLabel = '';
                                if (segments && nearCheckpoint.cpNumber > 0 && nearCheckpoint.cpNumber < segments.length) {
                                    prevLabel = segments[nearCheckpoint.cpNumber - 1].to;
                                    nextLabel = segments[nearCheckpoint.cpNumber].to;
                                } else {
                                    prevLabel = 'CP?';
                                    nextLabel = 'CP?';
                                }
                                const sectionLabel = `${prevLabel} to ${nextLabel} Details:`;
                                labels.push(toUnicodeBold(sectionLabel));
                                // Show gels/sachets needed for next section (from segment data), else carbs
                                let fuelLine = '';
                                // Find the next segment (this CP -> next CP)
                                let nextSegment = null;
                                if (segments && nearCheckpoint.cpNumber < segments.length) {
                                    nextSegment = segments[nearCheckpoint.cpNumber];
                                }
                                if (nextSegment && nextSegment.num_gels !== undefined && nextSegment.num_gels !== null && nextSegment.num_gels > 0) {
                                    fuelLine = `Fuel Needed: ${nextSegment.num_gels} gels/sachets`;
                                } else if (nextSegment && nextSegment.target_carbs !== undefined && nextSegment.target_carbs !== null) {
                                    fuelLine = `Fuel Needed: ${nextSegment.target_carbs}g carbs`;
                                } else {
                                    fuelLine = `Fuel Needed: ${nearCheckpoint.carbsToNext}g carbs`;
                                }
                                labels.push(fuelLine);
                                labels.push(`Hydration: ${nearCheckpoint.waterToNext}L water`);
                                // Add drop bag plan at the bottom if present
                                if (currentPlan && currentPlan.checkpoint_dropbags && currentPlan.checkpoint_dropbags[nearCheckpoint.cpNumber - 1]) {
                                    if (currentPlan.dropbag_contents && Array.isArray(currentPlan.dropbag_contents)) {
                                        const dropbag = currentPlan.dropbag_contents.find(db => {
                                            return (db.checkpoint === nearCheckpoint.label) || (db.cpNumber === nearCheckpoint.cpNumber);
                                        });
                                        if (dropbag) {
                                            labels.push('');
                                            const bolded = `${prevLabel} dropbag contents:`;
                                            labels.push(toUnicodeBold(bolded));
                                            let planLine = '';
                                            if (dropbag.num_gels !== undefined) {
                                                planLine = `Gels/Sachets: ${dropbag.num_gels}, Hydration: ${dropbag.hydration}L`;
                                            } else {
                                                planLine = `Carbs: ${dropbag.carbs}g, Hydration: ${dropbag.hydration}L`;
                                            }
                                            labels.push(planLine);
                                        }
                                    }
                                }
                            }
                            return labels;
                        },
                        labelTextColor: (context) => {
                            return '#1f2937';
                        }
                    },
                    backgroundColor: 'rgba(255, 255, 255, 0.95)',
                    titleColor: '#1f2937',
                    bodyColor: '#1f2937',
                    borderColor: 'rgba(0, 0, 0, 0.1)',
                    borderWidth: 1,
                    padding: 12,
                    displayColors: false,
                    titleFont: {
                        size: 13,
                        weight: 'bold'
                    },
                    bodyFont: {
                        size: 12
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
        },
        plugins: [checkpointLinesPlugin]
    });
}

function resetPlanState() {
    // Reset currentPlan state completely
    currentPlan = {
        gpx_filename: null,
        checkpoint_distances: [],
        checkpoint_dropbags: [],
        segment_terrain_types: [],
        segments: null,
        summary: null,
        elevation_profile: null,
        dropbag_contents: null,
        loadedFilename: null,
        loadedSource: null,
        planName: null,
        total_distance: null,
        is_known_race: false,
        race_start_time: null,
        pacing_mode: 'base_pace'
    };
    
    // Reset the race plan title to default
    updateRacePlanTitle();
    
    // Destroy elevation chart
    if (elevationChart) {
        elevationChart.destroy();
        elevationChart = null;
    }
    
    // Clear GPX info box
    gpxInfoBox.style.display = 'none';
    
    // Hide results
    resultsContainer.style.display = 'none';
    noResults.style.display = 'block';
    
    // Disable save/export buttons
    saveBtn.disabled = true;
    exportBtn.disabled = true;
}

function clearAllInputs() {
    // Reset state using resetPlanState
    resetPlanState();
    
    // Reset file input
    gpxFileInput.value = '';
    fileNameDisplay.textContent = 'Choose GPX file...';
    
    // Reset all inputs to defaults
    document.getElementById('num-checkpoints').value = 3;
    document.getElementById('avg-cp-time').value = 5;
    document.getElementById('z2-pace-min').value = 6;
    document.getElementById('z2-pace-sec').value = 30;
    document.getElementById('climbing-ability').value = 'moderate';
    document.getElementById('carbs-per-hour').value = 60;
    document.getElementById('water-per-hour').value = 500;
    document.getElementById('carbs-per-gel').value = '';
    document.getElementById('race-start-time').value = '';
    document.getElementById('fatigue-enabled').checked = true;
    document.getElementById('fitness-level').value = 'recreational';
    document.getElementById('fitness-level').disabled = false;
    document.getElementById('terrain-enabled').checked = false;
    document.getElementById('skill-level').value = 0.5;
    document.getElementById('default-terrain-type').value = '';
    terrainSkillContainer.style.display = 'none';
    
    // Regenerate checkpoint inputs with default value
    generateCheckpointInputs();
}

function clearAll() {
    if (!confirm('Are you sure you want to clear all data and start again?')) {
        return;
    }
    
    // Call the shared clear inputs function
    clearAllInputs();
}

async function handleGPXUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    // Reset all inputs to defaults when uploading a new GPX
    // This ensures a clean slate and prevents confusion when switching between plans
    // Per requirement: Call "Clear and Start again" logic before loading GPX
    clearAllInputs();

    // Set the file name display (clearAllInputs resets it, so we set it again)
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
            currentPlan.total_distance = data.total_distance;
            currentPlan.loadedFilename = null;  // Clear loaded filename when uploading new GPX

            gpxInfoBox.innerHTML = `
                <strong>Route Loaded:</strong><br>
                Distance: ${data.total_distance} km (${data.total_distance_miles} miles)<br>
                Elevation Gain: +${data.total_elev_gain} m / -${data.total_elev_loss} m<br>
                Trackpoints: ${data.num_trackpoints}
            `;
            gpxInfoBox.style.display = 'block';

            // Update summary cards for distance and elevation gain immediately
            document.getElementById('summary-distance').textContent = `${data.total_distance} km`;
            document.getElementById('summary-elev-gain').textContent = `+${data.total_elev_gain} m`;

            // Validate checkpoint distances now that we have total distance
            validateCheckpointDistances();

            // Fetch elevation profile for vertical plot (basic, no segments yet)
            // We'll call /api/calculate with only the GPX filename and no checkpoints to get the elevation_profile
            try {
                const profileResponse = await fetch('/api/calculate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        gpx_filename: data.filename,
                        checkpoint_distances: [],
                        checkpoint_dropbags: [],
                        segment_terrain_types: ['smooth_trail'],
                        avg_cp_time: 5,
                        z2_pace: 6.5,
                        climbing_ability: 'moderate',
                        carbs_per_hour: 60,
                        water_per_hour: 500,
                        fatigue_enabled: true,
                        fitness_level: 'recreational',
                        skill_level: 0.5
                    })
                });
                const profileData = await profileResponse.json();
                if (profileResponse.ok && profileData.elevation_profile && profileData.elevation_profile.length > 0) {
                    // Render the vertical profile with a dummy segments array (just Start→Finish)
                    renderElevationChart(profileData.elevation_profile, [
                        { from: 'Start', to: 'Finish', distance: data.total_distance }
                    ]);
                    // Show the results container and hide the placeholder
                    resultsContainer.style.display = 'block';
                    noResults.style.display = 'none';
                }
            } catch (e) {
                // Fail silently if profile can't be rendered
            }

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

function validateCheckpointDistances() {
    const inputs = document.querySelectorAll('.checkpoint-distance');
    const totalDistance = currentPlan.total_distance || 0;
    
    // Clear all previous errors
    inputs.forEach(input => {
        input.classList.remove('error');
        const errorMsg = document.getElementById(`checkpoint-error-${input.dataset.index}`);
        if (errorMsg) {
            errorMsg.textContent = '';
            errorMsg.classList.remove('visible');
        }
    });
    
    let hasErrors = false;
    const values = [];
    
    // First pass: collect values and check basic validation
    inputs.forEach((input, index) => {
        const value = parseFloat(input.value);
        const errorMsg = document.getElementById(`checkpoint-error-${index}`);
        
        // Check if it's a valid number
        if (input.value.trim() !== '' && (isNaN(value) || value < 0)) {
            input.classList.add('error');
            errorMsg.textContent = 'Must be a positive number';
            errorMsg.classList.add('visible');
            hasErrors = true;
            return;
        }
        
        // Check if greater than total distance
        if (!isNaN(value) && totalDistance > 0 && value > totalDistance) {
            input.classList.add('error');
            errorMsg.textContent = `Cannot exceed total distance (${totalDistance} km)`;
            errorMsg.classList.add('visible');
            hasErrors = true;
            return;
        }
        
        values.push(value);
    });
    
    // Second pass: check ordering and duplicates
    if (!hasErrors) {
        const validValues = values.filter(v => !isNaN(v));
        const sortedValues = [...validValues].sort((a, b) => a - b);
        
        // Check for duplicates
        for (let i = 0; i < sortedValues.length - 1; i++) {
            if (sortedValues[i] === sortedValues[i + 1]) {
                // Find which inputs have this duplicate value
                inputs.forEach((input, index) => {
                    const inputValue = parseFloat(input.value);
                    if (!isNaN(inputValue) && inputValue === sortedValues[i]) {
                        input.classList.add('error');
                        const errorMsg = document.getElementById(`checkpoint-error-${index}`);
                        errorMsg.textContent = 'Checkpoint distances cannot be equal';
                        errorMsg.classList.add('visible');
                        hasErrors = true;
                    }
                });
                break;
            }
        }
        
        // Check ordering (must be in ascending order)
        if (!hasErrors) {
            for (let i = 1; i < values.length; i++) {
                const currentVal = values[i];
                const prevVal = values[i-1];
                if (!isNaN(currentVal) && !isNaN(prevVal) && currentVal <= prevVal) {
                    inputs[i].classList.add('error');
                    const errorMsg = document.getElementById(`checkpoint-error-${i}`);
                    errorMsg.textContent = `Must be greater than CP${i} (${prevVal} km)`;
                    errorMsg.classList.add('visible');
                    hasErrors = true;
                }
            }
        }
    }
    
    return !hasErrors;
}

function updateCheckpointCounter(current, max) {
    if (checkpointCounter) {
        checkpointCounter.textContent = `(${current} / ${max})`;
    }
}

function generateCheckpointInputs() {
    const numCheckpoints = parseInt(numCheckpointsInput.value) || 0;
    checkpointDistancesContainer.innerHTML = '';
    
    // Update checkpoint counter
    updateCheckpointCounter(numCheckpoints, MAX_CHECKPOINTS);

    // Create checkpoint distance inputs with integrated dropbag toggle
    for (let i = 0; i < numCheckpoints; i++) {
        const div = document.createElement('div');
        div.className = 'checkpoint-input';
        
        const hasDropbag = currentPlan.checkpoint_dropbags[i] || false;
        
        div.innerHTML = `
            <label>Checkpoint ${i + 1} Distance (km):</label>
            <div class="checkpoint-input-wrapper">
                <input type="text" 
                       class="checkpoint-distance" 
                       data-index="${i}" 
                       step="0.1" 
                       min="0"
                       pattern="[0-9]*\.?[0-9]*"
                       inputmode="decimal"
                       value="${currentPlan.checkpoint_distances ? currentPlan.checkpoint_distances[i] || '' : ''}"
                       placeholder="e.g., 25.5" />
                <button type="button"
                        class="checkpoint-dropbag-toggle" 
                        data-index="${i}"
                        aria-pressed="${hasDropbag}"
                        aria-label="Toggle drop bag for checkpoint ${i + 1}">
                    Dropbag
                </button>
            </div>
            <div class="error-message" id="checkpoint-error-${i}"></div>
        `;
        checkpointDistancesContainer.appendChild(div);
    }

// Add event listeners for real-time updates
    document.querySelectorAll('.checkpoint-distance').forEach(input => {
        // Prevent non-numeric key presses
        input.addEventListener('keydown', (e) => {
            // Allow: backspace, delete, tab, escape, enter, and .
            if ([46, 8, 9, 27, 13, 110, 190].indexOf(e.keyCode) !== -1 ||
                // Allow: Ctrl+A, Ctrl+C, Ctrl+V, Ctrl+X, Ctrl+Z
                (e.ctrlKey === true && [65, 67, 86, 88, 90].indexOf(e.keyCode) !== -1) ||
                // Allow: home, end, left, right
                (e.keyCode >= 35 && e.keyCode <= 39)) {
                // Let it happen
                return;
            }
            // Ensure that it is a number and stop the keypress if not
            if ((e.shiftKey || (e.keyCode < 48 || e.keyCode > 57)) && (e.keyCode < 96 || e.keyCode > 105) && e.keyCode !== 190 && e.keyCode !== 110) {
                e.preventDefault();
            }
        });
        
        input.addEventListener('input', (e) => {
            // Remove any non-numeric characters except decimal point
            let value = e.target.value.replace(/[^0-9.]/g, '');
            // Ensure only one decimal point
            let parts = value.split('.');
            if (parts.length > 2) {
                value = parts[0] + '.' + parts.slice(1).join('');
            }
            e.target.value = value;
            validateCheckpointDistances();
            if (currentPlan.gpx_filename) {
                calculateRacePlan();
            }
        });
        input.addEventListener('change', () => {
            validateCheckpointDistances();
            if (currentPlan.gpx_filename) {
                calculateRacePlan();
            }
        });
    });
    
    // Add event listeners for dropbag toggle buttons
    document.querySelectorAll('.checkpoint-dropbag-toggle').forEach(button => {
        button.addEventListener('click', (e) => {
            const currentState = button.getAttribute('aria-pressed') === 'true';
            const newState = !currentState;
            button.setAttribute('aria-pressed', newState);
            button.textContent = 'Dropbag';
            
            if (currentPlan.gpx_filename) {
                calculateRacePlan();
            }
        });
    });
    
    // Generate terrain difficulty inputs if enabled
    if (terrainEnabledInput.checked) {
        generateTerrainDifficultyInputs();
    }
}

function generateTerrainDifficultyInputs() {
    const numCheckpoints = parseInt(numCheckpointsInput.value) || 0;
    terrainDifficultiesContainer.innerHTML = '';
    
    if (numCheckpoints === 0) {
        return;
    }

    // Create terrain type dropdowns for all segments
    // Note: We need numCheckpoints + 1 dropdowns for all segments (Start→CP1, CP1→CP2, ..., CPn→Finish)
    for (let i = 0; i < numCheckpoints; i++) {
        const div = document.createElement('div');
        div.className = 'checkpoint-input';
        const terrainType = currentPlan.segment_terrain_types?.[i] || 'smooth_trail';
        
        // Determine segment label (Start → CP1, CP1 → CP2, etc.)
        const fromLabel = i === 0 ? 'Start' : `CP${i}`;
        const toLabel = `CP${i + 1}`;
        
        div.innerHTML = `
            <label>Segment ${fromLabel} → ${toLabel} Terrain Type:</label>
            <select class="segment-terrain-type" data-index="${i}">
                <option value="road" ${terrainType === 'road' ? 'selected' : ''}>Road/Track (0.95×)</option>
                <option value="smooth_trail" ${terrainType === 'smooth_trail' ? 'selected' : ''}>Smooth Trail (1.0×)</option>
                <option value="dirt_road" ${terrainType === 'dirt_road' ? 'selected' : ''}>Dirt Road (1.05×)</option>
                <option value="rocky_runnable" ${terrainType === 'rocky_runnable' ? 'selected' : ''}>Rocky Runnable (1.15×)</option>
                <option value="technical" ${terrainType === 'technical' ? 'selected' : ''}>Technical Trail (1.325×)</option>
                <option value="very_technical" ${terrainType === 'very_technical' ? 'selected' : ''}>Very Technical (1.65×)</option>
                <option value="scrambling" ${terrainType === 'scrambling' ? 'selected' : ''}>Scrambling (2.0×)</option>
            </select>
        `;
        terrainDifficultiesContainer.appendChild(div);
    }
    
    // Add final segment terrain type (last CP → Finish)
    const div = document.createElement('div');
    div.className = 'checkpoint-input';
    const finalTerrainType = currentPlan.segment_terrain_types?.[numCheckpoints] || 'smooth_trail';
    const fromLabel = `CP${numCheckpoints}`;
    
    div.innerHTML = `
        <label>Segment ${fromLabel} → Finish Terrain Type:</label>
        <select class="segment-terrain-type" data-index="${numCheckpoints}">
            <option value="road" ${finalTerrainType === 'road' ? 'selected' : ''}>Road/Track (0.95×)</option>
            <option value="smooth_trail" ${finalTerrainType === 'smooth_trail' ? 'selected' : ''}>Smooth Trail (1.0×)</option>
            <option value="dirt_road" ${finalTerrainType === 'dirt_road' ? 'selected' : ''}>Dirt Road (1.05×)</option>
            <option value="rocky_runnable" ${finalTerrainType === 'rocky_runnable' ? 'selected' : ''}>Rocky Runnable (1.15×)</option>
            <option value="technical" ${finalTerrainType === 'technical' ? 'selected' : ''}>Technical Trail (1.325×)</option>
            <option value="very_technical" ${finalTerrainType === 'very_technical' ? 'selected' : ''}>Very Technical (1.65×)</option>
            <option value="scrambling" ${finalTerrainType === 'scrambling' ? 'selected' : ''}>Scrambling (2.0×)</option>
        </select>
    `;
    terrainDifficultiesContainer.appendChild(div);

    // Add event listeners for real-time updates
    document.querySelectorAll('.segment-terrain-type').forEach(input => {
        input.addEventListener('change', () => {
            if (currentPlan.gpx_filename) {
                calculateRacePlan();
            }
        });
    });
}

function handlePacingModeChange() {
    const selectedMode = document.querySelector('input[name="pacing-mode"]:checked').value;
    currentPlan.pacing_mode = selectedMode;
    
    if (selectedMode === 'base_pace') {
        basePaceInputs.style.display = 'block';
        targetTimeInputs.style.display = 'none';
        // Clear target time warning when switching to base pace mode
        if (targetTimeWarning) {
            targetTimeWarning.style.display = 'none';
        }
    } else {
        basePaceInputs.style.display = 'none';
        targetTimeInputs.style.display = 'block';
    }
    
    // Note: Climbing ability, fitness level, and fatigue settings are shown in both modes
    // - Base Pace Mode: They affect forward prediction (ability → pace → time)
    // - Target Time Mode: They affect effort allocation optimization (cost, capacity, limits)
    
    // Recalculate if a plan is loaded
    if (currentPlan.gpx_filename && currentPlan.checkpoint_distances.length > 0) {
        calculateRacePlan();
    }
}

async function calculateRacePlan() {
    if (!currentPlan.gpx_filename) {
        alert('Please upload a GPX file first');
        return;
    }

    // Validate checkpoint distances before proceeding
    if (!validateCheckpointDistances()) {
        return; // Don't calculate if there are validation errors
    }

    // Gather checkpoint distances
    const checkpointInputs = document.querySelectorAll('.checkpoint-distance');
    const checkpointDistances = Array.from(checkpointInputs)
        .map(input => parseFloat(input.value));
    
    // Gather checkpoint dropbag status - must align with checkpoint distances
    const dropbagToggleButtons = document.querySelectorAll('.checkpoint-dropbag-toggle');
    const checkpointDropbags = Array.from(dropbagToggleButtons)
        .map(button => button.getAttribute('aria-pressed') === 'true');
    
    // Filter out invalid distances and their corresponding dropbag values
    const validCheckpoints = [];
    const validDropbags = [];
    
    for (let i = 0; i < checkpointDistances.length; i++) {
        if (!isNaN(checkpointDistances[i])) {
            validCheckpoints.push(checkpointDistances[i]);
            validDropbags.push(checkpointDropbags[i] || false);
        }
    }
    
    currentPlan.checkpoint_distances = validCheckpoints;
    currentPlan.checkpoint_dropbags = validDropbags;

    // Gather segment terrain types (only if terrain difficulty is enabled)
    const terrainEnabled = terrainEnabledInput.checked;
    if (terrainEnabled) {
        const terrainInputs = document.querySelectorAll('.segment-terrain-type');
        // Sort by data-index to ensure correct order
        const sortedInputs = Array.from(terrainInputs).sort((a, b) => {
            return parseInt(a.getAttribute('data-index')) - parseInt(b.getAttribute('data-index'));
        });
        currentPlan.segment_terrain_types = sortedInputs.map(input => input.value);
    } else {
        // Set all terrain types to 'smooth_trail' (baseline) if terrain is disabled
        const numSegments = currentPlan.checkpoint_distances.length + 1;
        currentPlan.segment_terrain_types = Array(numSegments).fill('smooth_trail');
    }

    // Gather other inputs
    const avgCpTime = parseFloat(document.getElementById('avg-cp-time').value) || 5;
    
    // Parse pace components - handle zero values properly (0 is valid for seconds)
    const z2PaceMinValue = document.getElementById('z2-pace-min').value;
    const z2PaceSecValue = document.getElementById('z2-pace-sec').value;
    const z2PaceMin = z2PaceMinValue === '' ? 6 : parseFloat(z2PaceMinValue);
    const z2PaceSec = z2PaceSecValue === '' ? 30 : parseFloat(z2PaceSecValue);
    const z2Pace = z2PaceMin + z2PaceSec / 60;
    const climbingAbility = document.getElementById('climbing-ability').value || 'moderate';
    const carbsPerHour = parseFloat(document.getElementById('carbs-per-hour').value) || 60;
    const waterPerHour = parseFloat(document.getElementById('water-per-hour').value) || 500;
    const raceStartTime = document.getElementById('race-start-time').value || null;
    const fatigueEnabled = document.getElementById('fatigue-enabled').checked;
    const fitnessLevel = document.getElementById('fitness-level').value;
    const skillLevel = parseFloat(document.getElementById('skill-level').value) || 0.5;
    
    // Get carbs per gel (optional)
    const carbsPerGelInput = document.getElementById('carbs-per-gel').value;
    const carbsPerGel = carbsPerGelInput && carbsPerGelInput.trim() !== '' ? parseFloat(carbsPerGelInput) : null;
    
    // Get pacing mode and target time
    const pacingMode = currentPlan.pacing_mode;
    let targetTime = null;
    if (pacingMode === 'target_time') {
        const hours = parseInt(targetTimeHoursInput.value) || 0;
        const minutes = parseInt(targetTimeMinutesInput.value) || 0;
        const seconds = parseInt(targetTimeSecondsInput.value) || 0;
        
        if (hours === 0 && minutes === 0 && seconds === 0) {
            alert('Please enter a target finish time');
            return;
        }
        
        targetTime = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }

    const requestData = {
        gpx_filename: currentPlan.gpx_filename,
        is_known_race: currentPlan.is_known_race || false,
        checkpoint_distances: currentPlan.checkpoint_distances,
        checkpoint_dropbags: currentPlan.checkpoint_dropbags,
        segment_terrain_types: currentPlan.segment_terrain_types,
        avg_cp_time: avgCpTime,
        z2_pace: z2Pace,
        climbing_ability: climbingAbility,
        carbs_per_hour: carbsPerHour,
        water_per_hour: waterPerHour,
        carbs_per_gel: carbsPerGel,
        race_start_time: raceStartTime,
        fatigue_enabled: fatigueEnabled,
        fitness_level: fitnessLevel,
        skill_level: skillLevel,
        pacing_mode: pacingMode,
        target_time: targetTime
    };

    // Include elevation profile if available (from loaded plan)
    if (currentPlan.elevation_profile) {
        requestData.elevation_profile = currentPlan.elevation_profile;
    }

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
            // Update elevation profile if returned (in case it was recalculated)
            if (data.elevation_profile) {
                currentPlan.elevation_profile = data.elevation_profile;
            }
            
            // Handle target time warning if present
            const targetTimeWarning = document.getElementById('target-time-warning');
            if (data.target_time_warning) {
                targetTimeWarning.textContent = data.target_time_warning;
                targetTimeWarning.style.display = 'block';
            } else {
                targetTimeWarning.style.display = 'none';
            }
            
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
    const { segments, summary, elevation_profile, dropbag_contents, effort_thresholds } = data;

    // Store elevation profile and dropbag contents
    currentPlan.elevation_profile = elevation_profile;
    currentPlan.dropbag_contents = dropbag_contents;
    
    // Render elevation chart if profile exists
    if (elevation_profile && elevation_profile.length > 0) {
        renderElevationChart(elevation_profile, segments);
    }

    // Update summary cards
    document.getElementById('summary-distance').textContent = `${summary.total_distance} km`;
    document.getElementById('summary-moving-time').textContent = summary.total_moving_time_str;
    document.getElementById('summary-cp-time').textContent = summary.total_cp_time_str;
    document.getElementById('summary-total-time').textContent = summary.total_race_time_str;
    document.getElementById('summary-elev-gain').textContent = `${summary.total_elev_gain} m`;
    document.getElementById('summary-carbs').textContent = `${summary.total_carbs} g`;
    document.getElementById('summary-water').textContent = `${summary.total_water} L`;
    
    // Display effort thresholds if in target time mode
    const thresholdsContainer = document.getElementById('effort-thresholds-container');
    if (effort_thresholds && thresholdsContainer) {
        thresholdsContainer.style.display = 'block';
        
        // Format times as HH:MM:SS
        const formatMinutesToTime = (minutes) => {
            const hours = Math.floor(minutes / 60);
            const mins = Math.floor(minutes % 60);
            const secs = Math.floor((minutes % 1) * 60);
            return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        };
        
        document.getElementById('threshold-natural').textContent = formatMinutesToTime(effort_thresholds.natural_time_minutes);
        document.getElementById('threshold-push').textContent = formatMinutesToTime(effort_thresholds.push_threshold_minutes);
        document.getElementById('threshold-protect').textContent = formatMinutesToTime(effort_thresholds.protect_threshold_minutes);
    } else if (thresholdsContainer) {
        thresholdsContainer.style.display = 'none';
    }

    // Update segments table
    const tbody = document.getElementById('segments-tbody');
    tbody.innerHTML = '';

    const hasTimeOfDay = segments.some(seg => seg.time_of_day !== null);
    const timeOfDayCols = document.querySelectorAll('.time-of-day-col');
    timeOfDayCols.forEach(col => {
        col.style.display = hasTimeOfDay ? 'table-cell' : 'none';
    });

    // Check if fatigue is enabled to show/hide fatigue column
    const fatigueEnabled = document.getElementById('fatigue-enabled').checked;
    const hasFatigue = fatigueEnabled && segments.some(seg => seg.fatigue_seconds > 0);
    const fatigueCols = document.querySelectorAll('.fatigue-col');
    fatigueCols.forEach(col => {
        col.style.display = hasFatigue ? 'table-cell' : 'none';
    });

    // Check if terrain is enabled to show/hide terrain columns
    const terrainEnabled = document.getElementById('terrain-enabled').checked;
    const terrainCols = document.querySelectorAll('.terrain-col');
    terrainCols.forEach(col => {
        col.style.display = terrainEnabled ? 'table-cell' : 'none';
    });

    segments.forEach(seg => {
        const row = document.createElement('tr');
        
        // Determine pace styling based on mode
        let paceStyle = 'font-weight: bold;';
        let paceWarning = '';
        let effortBadge = '';
        
        if (seg.pace_capped) {
            paceStyle = 'color: #ef4444; font-weight: bold;';
            paceWarning = ' ⚠️';
        } else if (seg.pace_aggressive) {
            // Highlight aggressive paces (faster than typical for the segment)
            paceStyle = 'color: #f59e0b; font-weight: bold;';
            paceWarning = ' ⚡';
        }
        
        // Add effort level badge in target time mode only
        if (effort_thresholds && seg.effort_level) {
            const effortLabels = {
                'push': '<span class="effort-badge effort-push">PUSH</span>',
                'steady': '<span class="effort-badge effort-steady">Steady</span>',
                'protect': '<span class="effort-badge effort-protect">Protect</span>'
            };
            effortBadge = effortLabels[seg.effort_level] || '';
        }
        
        const timeOfArrival = seg.time_of_day ? `${seg.time_of_day} at ${seg.to}` : '--';
        
        // Format terrain type for display
        const terrainTypeDisplay = seg.terrain_type ? seg.terrain_type.replace(/_/g, ' ') : 'smooth trail';
        const terrainFactorDisplay = seg.terrain_factor ? `${seg.terrain_factor.toFixed(2)}x` : '1.00x';
        
        row.innerHTML = `
            <td><strong>${seg.from} → ${seg.to}</strong></td>
            <td>${seg.cumulative_distance}</td>
            <td>+${seg.elev_gain}/-${seg.elev_loss}</td>
            <td>${seg.net_elev > 0 ? '+' : ''}${seg.net_elev}</td>
            <td>${seg.elev_pace_str}</td>
            <td class="fatigue-col" style="display: ${hasFatigue ? 'table-cell' : 'none'}">${seg.fatigue_str}</td>
            <td class="terrain-col" style="display: ${terrainEnabled ? 'table-cell' : 'none'}">${terrainFactorDisplay}</td>
            <td><strong style="${paceStyle}">${seg.pace_str}${paceWarning}</strong> ${effortBadge}</td>
            <td>${seg.segment_time_str}</td>
            <td>${seg.target_carbs}</td>
            <td>${seg.target_water}</td>
            <td><strong>${seg.cumulative_time_str}</strong></td>
            <td class="time-of-day-col" style="display: ${hasTimeOfDay ? 'table-cell' : 'none'}">
                ${timeOfArrival}
            </td>
        `;
        tbody.appendChild(row);
    });

    // Render dropbag table if dropbag_contents exists
    const dropbagTableContainer = document.getElementById('dropbag-table-container');
    const dropbagTbody = document.getElementById('dropbag-tbody');
    const dropbagTableHeader = document.querySelector('#dropbag-table thead tr');
    
    if (dropbag_contents && dropbag_contents.length > 0) {
        dropbagTbody.innerHTML = '';
        
        // Check if gel columns should be displayed (if any item has num_gels)
        const hasGelData = dropbag_contents.some(item => item.num_gels !== undefined);
        
        // Update table header based on whether gel data is present
        if (hasGelData) {
            dropbagTableHeader.innerHTML = `
                <th>Checkpoint</th>
                <th>Carb Target (g)</th>
                <th>Number of Gels</th>
                <th>Actual Carbs (g)</th>
                <th>Hydration Target (L)</th>
            `;
        } else {
            dropbagTableHeader.innerHTML = `
                <th>Checkpoint</th>
                <th>Carb Target (g)</th>
                <th>Hydration Target (L)</th>
            `;
        }
        
        // Render rows
        dropbag_contents.forEach(item => {
            const row = document.createElement('tr');
            
            if (hasGelData) {
                row.innerHTML = `
                    <td><strong>${item.checkpoint}</strong></td>
                    <td>${item.carbs}</td>
                    <td>${item.num_gels}</td>
                    <td>${item.actual_carbs}</td>
                    <td>${item.hydration}</td>
                `;
            } else {
                row.innerHTML = `
                    <td><strong>${item.checkpoint}</strong></td>
                    <td>${item.carbs}</td>
                    <td>${item.hydration}</td>
                `;
            }
            
            dropbagTbody.appendChild(row);
        });
        
        dropbagTableContainer.style.display = 'block';
    } else {
        dropbagTableContainer.style.display = 'none';
    }

    // Show results
    noResults.style.display = 'none';
    resultsContainer.style.display = 'block';
}

function showSaveModal() {
    if (!currentPlan.segments) {
        alert('Please calculate a race plan first');
        return;
    }
    
    // If a plan is loaded, show both Save and Save As buttons
    if (currentPlan.loadedFilename) {
        // Set the plan name to the loaded filename (without .json extension)
        const loadedPlanName = currentPlan.loadedFilename.replace(/\.json$/, '');
        planNameInput.value = loadedPlanName;
        
        // Show Save As button for loaded plans
        saveAsBtn.style.display = 'inline-block';
    } else {
        // Generate default name for new plans
        const now = new Date();
        const defaultName = `race_plan_${now.getFullYear()}${(now.getMonth()+1).toString().padStart(2,'0')}${now.getDate().toString().padStart(2,'0')}`;
        planNameInput.value = defaultName;
        
        // Hide Save As button for new plans
        saveAsBtn.style.display = 'none';
    }
    
    saveModal.classList.add('active');
}

function showLoadModal() {
    loadModal.classList.add('active');
    loadSavedPlans();
}

function hideModal(modal) {
    modal.classList.remove('active');
}

async function savePlan(forceSaveAs = false) {
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
        force_save_as: forceSaveAs,  // Let backend know this is a Save As operation
        gpx_filename: currentPlan.gpx_filename,
        checkpoint_distances: currentPlan.checkpoint_distances,
        checkpoint_dropbags: currentPlan.checkpoint_dropbags,
        segment_terrain_types: currentPlan.segment_terrain_types,
        avg_cp_time: parseFloat(document.getElementById('avg-cp-time').value),
        z2_pace: parseFloat(document.getElementById('z2-pace-min').value) + parseFloat(document.getElementById('z2-pace-sec').value) / 60,
        climbing_ability: document.getElementById('climbing-ability').value,
        carbs_per_hour: parseFloat(document.getElementById('carbs-per-hour').value),
        water_per_hour: parseFloat(document.getElementById('water-per-hour').value),
        carbs_per_gel: document.getElementById('carbs-per-gel').value ? parseFloat(document.getElementById('carbs-per-gel').value) : null,
        race_start_time: document.getElementById('race-start-time').value || null,
        fatigue_enabled: document.getElementById('fatigue-enabled').checked,
        fitness_level: document.getElementById('fitness-level').value,
        skill_level: parseFloat(document.getElementById('skill-level').value),
        segments: currentPlan.segments,
        summary: currentPlan.summary,
        elevation_profile: currentPlan.elevation_profile,
        dropbag_contents: currentPlan.dropbag_contents
    };

    try {
        // Get auth headers from auth manager
        const headers = await authManager.getAuthHeaders();
        
        const response = await fetch('/api/save-plan', {
            method: 'POST',
            headers: headers,
            body: JSON.stringify(saveData)
        });

        const data = await response.json();

        if (response.ok) {
            // Determine if this was an update or a new save
            const wasUpdate = !forceSaveAs && currentPlan.loadedFilename;
            
            // Always update to the filename returned by the server
            currentPlan.loadedFilename = data.filename;
            
            // Update the plan name to match what was saved
            currentPlan.planName = planName;
            
            // Update the UI title to reflect the new plan name
            updateRacePlanTitle(currentPlan.planName);
            
            // Mark that user has saved plans (for anonymous notice)
            localStorage.setItem('has_saved_plans', 'true');
            
            // Show appropriate message based on operation
            if (wasUpdate) {
                alert('Plan updated successfully!');
            } else {
                alert('Plan saved successfully!');
            }
            hideModal(saveModal);
        } else if (response.status === 409) {
            // Conflict - plan already exists
            alert(data.error);
            // Keep modal open so user can rename
        } else {
            alert('Error saving plan: ' + data.error);
        }
    } catch (error) {
        alert('Error saving plan: ' + error.message);
    }
}

async function loadSavedPlans() {
    try {
        // Get auth headers from auth manager
        const headers = await authManager.getAuthHeaders();
        
        const response = await fetch('/api/list-plans', {
            headers: headers
        });
        const data = await response.json();

        if (response.ok) {
            plansList.innerHTML = '';
            
            if (data.plans.length === 0) {
                plansList.innerHTML = '<p style="text-align: center; color: #64748b;">No saved plans found</p>';
                return;
            }

            // Check if we have local plans and user is authenticated - show migration prompt
            const hasLocalPlans = data.plans.some(p => p.source === 'local');
            const isAuthenticated = authManager.currentUser !== null;
            
            if (hasLocalPlans && isAuthenticated) {
                // Add migration prompt at the top
                const migrationDiv = document.createElement('div');
                migrationDiv.className = 'migration-prompt';
                migrationDiv.innerHTML = `
                    <div class="migration-prompt-content">
                        <span class="mdi mdi-cloud-upload"></span>
                        <span>You have local plans. <a href="#" id="migrate-local-plans-link">Import them to your account</a></span>
                    </div>
                `;
                plansList.appendChild(migrationDiv);
                
                // Add click handler for migration link
                document.getElementById('migrate-local-plans-link').addEventListener('click', (e) => {
                    e.preventDefault();
                    showLocalMigrationModal();
                });
            }

            data.plans.forEach(plan => {
                const div = document.createElement('div');
                div.className = 'plan-item';
                
                // Add source badge
                let sourceBadge;
                if (plan.source === 'local') {
                    sourceBadge = '<span class="plan-source-badge plan-source-local">Local</span>';
                } else if (plan.source === 'unowned') {
                    sourceBadge = '<span class="plan-source-badge plan-source-unowned">Unowned</span>';
                } else {
                    sourceBadge = '<span class="plan-source-badge plan-source-cloud">Account</span>';
                }
                
                div.innerHTML = `
                    <div class="plan-info">
                        <div class="plan-name">
                            ${plan.name}
                            ${sourceBadge}
                        </div>
                        <div class="plan-date">${formatTimestampToLocal(plan.modified)}</div>
                    </div>
                    <button class="plan-delete" data-filename="${plan.filename}" data-source="${plan.source}">Delete</button>
                `;
                
                div.querySelector('.plan-info').addEventListener('click', () => loadPlan(plan.filename, plan.source));
                div.querySelector('.plan-delete').addEventListener('click', (e) => {
                    e.stopPropagation();
                    deletePlan(plan.filename, plan.source);
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

async function importUnownedPlans() {
    try {
        const response = await fetch('/api/list-unowned-plans');
        const data = await response.json();

        if (response.ok) {
            plansList.innerHTML = '';
            
            if (data.plans.length === 0) {
                plansList.innerHTML = '<p style="text-align: center; color: #64748b;">No unowned or local plans found</p>';
                return;
            }

            // Add info message
            const infoDiv = document.createElement('div');
            infoDiv.className = 'migration-prompt';
            infoDiv.innerHTML = `
                <div class="migration-prompt-content">
                    <span class="mdi mdi-information"></span>
                    <span>Showing local and unowned plans. Click a plan to load it, or claim it to add to your account.</span>
                </div>
            `;
            plansList.appendChild(infoDiv);

            data.plans.forEach(plan => {
                const div = document.createElement('div');
                div.className = 'plan-item';
                
                // Add source badge
                let sourceBadge;
                if (plan.source === 'local') {
                    sourceBadge = '<span class="plan-source-badge plan-source-local">Local</span>';
                } else if (plan.source === 'unowned') {
                    sourceBadge = '<span class="plan-source-badge plan-source-unowned">Unowned</span>';
                }
                
                // Add action buttons based on source and authentication status
                let actionButtons = '';
                if (plan.source === 'unowned' && authManager.currentUser) {
                    // For unowned plans, show claim button if user is authenticated
                    actionButtons = `
                        <button class="plan-claim" data-plan-id="${plan.plan_id}" data-filename="${plan.filename}">Claim</button>
                    `;
                } else if (plan.source === 'local' && authManager.currentUser) {
                    // For local plans, show import button if user is authenticated
                    actionButtons = `
                        <button class="plan-import" data-filename="${plan.filename}">Import to Account</button>
                    `;
                }
                
                div.innerHTML = `
                    <div class="plan-info">
                        <div class="plan-name">
                            ${plan.name}
                            ${sourceBadge}
                        </div>
                        <div class="plan-date">${formatTimestampToLocal(plan.modified)}</div>
                    </div>
                    ${actionButtons}
                `;
                
                div.querySelector('.plan-info').addEventListener('click', () => loadPlan(plan.filename, plan.source));
                
                // Add handlers for action buttons
                const claimBtn = div.querySelector('.plan-claim');
                if (claimBtn) {
                    claimBtn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        claimUnownedPlan(plan.plan_id, plan.filename);
                    });
                }
                
                const importBtn = div.querySelector('.plan-import');
                if (importBtn) {
                    importBtn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        importLocalPlanToAccount(plan.filename);
                    });
                }
                
                plansList.appendChild(div);
            });
        } else {
            alert('Error loading unowned plans: ' + data.error);
        }
    } catch (error) {
        alert('Error loading unowned plans: ' + error.message);
    }
}

async function claimUnownedPlan(planId, filename) {
    if (!confirm(`Claim this plan and add it to your account?`)) {
        return;
    }
    
    try {
        const headers = await authManager.getAuthHeaders();
        
        const response = await fetch('/api/auth/claim-unowned-plan', {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({ plan_id: planId })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert('Plan claimed successfully!');
            // Reload the unowned plans list
            importUnownedPlans();
        } else {
            alert('Error claiming plan: ' + data.error);
        }
    } catch (error) {
        alert('Error claiming plan: ' + error.message);
    }
}

async function importLocalPlanToAccount(filename) {
    if (!confirm(`Import this local plan to your account?`)) {
        return;
    }
    
    try {
        const headers = await authManager.getAuthHeaders();
        
        const response = await fetch('/api/auth/migrate-local-plan', {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({ filename: filename })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert('Plan imported successfully!');
            // Reload the unowned plans list
            importUnownedPlans();
        } else {
            alert('Error importing plan: ' + data.error);
        }
    } catch (error) {
        alert('Error importing plan: ' + error.message);
    }
}

async function loadPlan(filename, source = 'local') {
    try {
        // Get auth headers from auth manager
        const headers = await authManager.getAuthHeaders();
        
        const response = await fetch(`/api/load-plan/${filename}?source=${source}`, {
            headers: headers
        });
        const data = await response.json();

        if (response.ok) {
            // Track the loaded filename for save/save-as functionality
            currentPlan.loadedFilename = filename;
            currentPlan.loadedSource = source;  // Track source for future saves
            
            // Store plan name (from data or filename without .json)
            currentPlan.planName = data.plan_name || filename.replace(/\.json$/, '');
            
            // Update the race plan title to show the loaded plan name
            updateRacePlanTitle(currentPlan.planName);
            
            // Load plan data into form
            currentPlan.gpx_filename = data.gpx_filename;
            currentPlan.checkpoint_distances = data.checkpoint_distances || [];
            currentPlan.checkpoint_dropbags = data.checkpoint_dropbags || [];
            currentPlan.segment_terrain_types = data.segment_terrain_types || [];
            
            // Set total_distance early (before validation) to avoid showing stale distance in error messages
            if (data.summary && data.summary.total_distance !== undefined && data.summary.total_distance !== null) {
                currentPlan.total_distance = data.summary.total_distance;
            }
            
            // Update the GPX file display to show the loaded GPX filename
            if (data.gpx_filename) {
                fileNameDisplay.textContent = data.gpx_filename;
            }
            
            document.getElementById('num-checkpoints').value = currentPlan.checkpoint_distances.length;
            document.getElementById('avg-cp-time').value = data.avg_cp_time || 5;
            
            const z2Pace = data.z2_pace || 6.5;
            let paceMin = Math.floor(z2Pace);
            let paceSec = Math.round((z2Pace % 1) * 60);
            
            // Handle seconds overflow due to floating-point rounding
            // When converting decimal minutes back to MM:SS format, values like 4.999
            // can round to 60 seconds (4:60), which should be normalized to 5:00
            if (paceSec >= 60) {
                paceMin += 1;
                paceSec = 0;
            }
            
            document.getElementById('z2-pace-min').value = paceMin;
            document.getElementById('z2-pace-sec').value = paceSec;
            
            document.getElementById('climbing-ability').value = data.climbing_ability || 'moderate';
            document.getElementById('carbs-per-hour').value = data.carbs_per_hour || 60;
            document.getElementById('water-per-hour').value = data.water_per_hour || 500;
            document.getElementById('carbs-per-gel').value = data.carbs_per_gel || '';
            document.getElementById('race-start-time').value = data.race_start_time || '';
            document.getElementById('fatigue-enabled').checked = data.fatigue_enabled !== undefined ? data.fatigue_enabled : true;
            document.getElementById('fitness-level').value = data.fitness_level || 'recreational';
            document.getElementById('fitness-level').disabled = !document.getElementById('fatigue-enabled').checked;
            
            // Load terrain settings
            const hasTerrainTypes = data.segment_terrain_types && data.segment_terrain_types.some(t => t !== 'smooth_trail');
            document.getElementById('terrain-enabled').checked = hasTerrainTypes;
            document.getElementById('skill-level').value = data.skill_level || 0.5;
            terrainSkillContainer.style.display = hasTerrainTypes ? 'block' : 'none';

            // Generate checkpoint inputs and populate (this will restore dropbag checkboxes)
            generateCheckpointInputs();

            // Validate checkpoint distances
            validateCheckpointDistances();

            // Load results if available
            if (data.segments && data.summary) {
                currentPlan.segments = data.segments;
                currentPlan.summary = data.summary;
                currentPlan.total_distance = data.summary.total_distance;
                currentPlan.race_start_time = data.race_start_time;
                currentPlan.elevation_profile = data.elevation_profile || null;
                currentPlan.dropbag_contents = data.dropbag_contents || null;
                
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

async function deletePlan(filename, source = 'local') {
    if (!confirm('Are you sure you want to delete this plan?')) {
        return;
    }

    try {
        // Get auth headers from auth manager
        const headers = await authManager.getAuthHeaders();
        
        const response = await fetch(`/api/delete-plan/${filename}?source=${source}`, {
            method: 'DELETE',
            headers: headers
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

function showExportImportModal() {
    // Enable/disable export button based on whether a plan is loaded
    if (currentPlan.segments && currentPlan.segments.length > 0) {
        exportPlanBtn.disabled = false;
    } else {
        exportPlanBtn.disabled = true;
    }
    exportImportModal.classList.add('active');
}

async function exportCurrentPlan() {
    if (!currentPlan.segments) {
        alert('Please calculate or load a race plan first');
        return;
    }

    // Gather all current plan data
    const planData = {
        plan_name: currentPlan.loadedFilename ? currentPlan.loadedFilename.replace('.json', '') : 'race_plan',
        gpx_filename: currentPlan.gpx_filename,
        checkpoint_distances: currentPlan.checkpoint_distances,
        checkpoint_dropbags: currentPlan.checkpoint_dropbags,
        segment_terrain_types: currentPlan.segment_terrain_types,
        avg_cp_time: parseFloat(document.getElementById('avg-cp-time').value) || 5,
        z2_pace: parseFloat(document.getElementById('z2-pace-min').value) + 
                 parseFloat(document.getElementById('z2-pace-sec').value) / 60,
        climbing_ability: document.getElementById('climbing-ability').value,
        carbs_per_hour: parseFloat(document.getElementById('carbs-per-hour').value) || 60,
        water_per_hour: parseFloat(document.getElementById('water-per-hour').value) || 500,
        carbs_per_gel: document.getElementById('carbs-per-gel').value ? 
                       parseFloat(document.getElementById('carbs-per-gel').value) : null,
        race_start_time: document.getElementById('race-start-time').value || null,
        fatigue_enabled: document.getElementById('fatigue-enabled').checked,
        fitness_level: document.getElementById('fitness-level').value,
        skill_level: parseFloat(document.getElementById('skill-level').value),
        segments: currentPlan.segments,
        summary: currentPlan.summary,
        elevation_profile: currentPlan.elevation_profile,
        dropbag_contents: currentPlan.dropbag_contents
    };

    try {
        const response = await fetch('/api/export-plan', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(planData)
        });

        const data = await response.json();

        if (response.ok) {
            // Create a Blob with the JSON data
            const jsonStr = JSON.stringify(data, null, 2);
            const blob = new Blob([jsonStr], { type: 'application/json' });
            
            // Create download link
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            const planName = planData.plan_name || 'race_plan';
            a.download = `${planName}_${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            alert('Plan exported successfully!');
            hideModal(exportImportModal);
        } else {
            alert('Error exporting plan: ' + data.error);
        }
    } catch (error) {
        alert('Error exporting plan: ' + error.message);
    }
}

async function handleImportPlan(event) {
    const file = event.target.files[0];
    if (!file) {
        return;
    }

    // Reset the file input so the same file can be selected again
    event.target.value = '';

    try {
        // Read the file
        const text = await file.text();
        let importData;
        
        try {
            importData = JSON.parse(text);
        } catch (e) {
            alert('Error: Invalid JSON file. Please select a valid JSON file exported from RaceCraft.');
            return;
        }

        // Confirm import
        const confirmed = confirm(
            'This will replace your current plan with the imported plan.\n\n' +
            'Do you want to continue?'
        );

        if (!confirmed) {
            return;
        }

        // Send to backend for validation
        const response = await fetch('/api/import-plan', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(importData)
        });

        const result = await response.json();

        if (response.ok) {
            // Load the imported plan data into the form
            const data = result.plan;
            
            // Clear current plan tracking
            currentPlan.loadedFilename = null;
            
            // Store plan name (from data or use a timestamped default)
            currentPlan.planName = data.plan_name || `Imported Plan ${new Date().toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}`;
            
            // Update the race plan title to show the imported plan name
            updateRacePlanTitle(currentPlan.planName);
            
            // Load plan data into form
            currentPlan.gpx_filename = data.gpx_filename;
            currentPlan.checkpoint_distances = data.checkpoint_distances || [];
            currentPlan.checkpoint_dropbags = data.checkpoint_dropbags || [];
            currentPlan.segment_terrain_types = data.segment_terrain_types || [];
            
            document.getElementById('num-checkpoints').value = currentPlan.checkpoint_distances.length;
            document.getElementById('avg-cp-time').value = data.avg_cp_time || 5;
            
            const z2Pace = data.z2_pace || 6.5;
            let paceMin = Math.floor(z2Pace);
            let paceSec = Math.round((z2Pace % 1) * 60);
            
            // Handle seconds overflow due to floating-point rounding
            // When converting decimal minutes back to MM:SS format, values like 4.999
            // can round to 60 seconds (4:60), which should be normalized to 5:00
            if (paceSec >= 60) {
                paceMin += 1;
                paceSec = 0;
            }
            
            document.getElementById('z2-pace-min').value = paceMin;
            document.getElementById('z2-pace-sec').value = paceSec;
            
            document.getElementById('climbing-ability').value = data.climbing_ability || 'moderate';
            document.getElementById('carbs-per-hour').value = data.carbs_per_hour || 60;
            document.getElementById('water-per-hour').value = data.water_per_hour || 500;
            document.getElementById('carbs-per-gel').value = data.carbs_per_gel || '';
            document.getElementById('race-start-time').value = data.race_start_time || '';
            document.getElementById('fatigue-enabled').checked = data.fatigue_enabled !== undefined ? data.fatigue_enabled : true;
            document.getElementById('fitness-level').value = data.fitness_level || 'recreational';
            document.getElementById('fitness-level').disabled = !document.getElementById('fatigue-enabled').checked;
            
            // Load terrain settings
            const hasTerrainTypes = data.segment_terrain_types && data.segment_terrain_types.some(t => t !== 'smooth_trail');
            document.getElementById('terrain-enabled').checked = hasTerrainTypes;
            document.getElementById('skill-level').value = data.skill_level || 0.5;
            terrainSkillContainer.style.display = hasTerrainTypes ? 'block' : 'none';

            // Generate checkpoint inputs
            generateCheckpointInputs();

            // Load results if available
            if (data.segments && data.summary) {
                currentPlan.segments = data.segments;
                currentPlan.summary = data.summary;
                currentPlan.total_distance = data.summary.total_distance;
                currentPlan.race_start_time = data.race_start_time;
                currentPlan.elevation_profile = data.elevation_profile || null;
                currentPlan.dropbag_contents = data.dropbag_contents || null;
                
                displayResults(data);
                
                saveBtn.disabled = false;
                exportBtn.disabled = false;
            }

            hideModal(exportImportModal);
            alert('Plan imported successfully!');
        } else {
            alert('Error importing plan: ' + result.error);
        }
    } catch (error) {
        alert('Error importing plan: ' + error.message);
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
        race_start_time: currentPlan.race_start_time,
        dropbag_contents: currentPlan.dropbag_contents || []
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

// Input filtering functions
function setupIntegerInput(inputElement) {
    inputElement.addEventListener('keydown', function(e) {
        // Allow: backspace, delete, tab, escape, enter, and .
        if ([46, 8, 9, 27, 13, 110].indexOf(e.keyCode) !== -1 ||
            // Allow: Ctrl+A, Ctrl+C, Ctrl+V, Ctrl+X, Ctrl+Z
            (e.keyCode === 65 && e.ctrlKey === true) ||
            (e.keyCode === 67 && e.ctrlKey === true) ||
            (e.keyCode === 86 && e.ctrlKey === true) ||
            (e.keyCode === 88 && e.ctrlKey === true) ||
            (e.keyCode === 90 && e.ctrlKey === true) ||
            // Allow: home, end, left, right
            (e.keyCode >= 35 && e.keyCode <= 39)) {
            return;
        }
        // Ensure that it is a number and stop the keypress
        if ((e.shiftKey || (e.keyCode < 48 || e.keyCode > 57)) && (e.keyCode < 96 || e.keyCode > 105)) {
            e.preventDefault();
        }
    });

    inputElement.addEventListener('input', function(e) {
        // Remove any non-numeric characters
        this.value = this.value.replace(/[^0-9]/g, '');
    });
}

function setupDecimalInput(inputElement) {
    inputElement.addEventListener('keydown', function(e) {
        // Allow: backspace, delete, tab, escape, enter, and .
        if ([46, 8, 9, 27, 13, 110, 190].indexOf(e.keyCode) !== -1 ||
            // Allow: Ctrl+A, Ctrl+C, Ctrl+V, Ctrl+X, Ctrl+Z
            (e.keyCode === 65 && e.ctrlKey === true) ||
            (e.keyCode === 67 && e.ctrlKey === true) ||
            (e.keyCode === 86 && e.ctrlKey === true) ||
            (e.keyCode === 88 && e.ctrlKey === true) ||
            (e.keyCode === 90 && e.ctrlKey === true) ||
            // Allow: home, end, left, right
            (e.keyCode >= 35 && e.keyCode <= 39)) {
            return;
        }
        // Ensure that it is a number and stop the keypress
        if ((e.shiftKey || (e.keyCode < 48 || e.keyCode > 57)) && (e.keyCode < 96 || e.keyCode > 105)) {
            e.preventDefault();
        }
    });

    inputElement.addEventListener('input', function(e) {
        // Remove any non-numeric characters except decimal point
        let value = this.value.replace(/[^0-9.]/g, '');
        // Ensure only one decimal point
        let parts = value.split('.');
        if (parts.length > 2) {
            value = parts[0] + '.' + parts.slice(1).join('');
        }
        this.value = value;
    });
}

function setupNumericInputFiltering() {
    // Integer inputs
    const integerInputs = [
        'z2-pace-min',
        'z2-pace-sec'
    ];

    // Decimal inputs
    const decimalInputs = [
        'avg-cp-time',
        'carbs-per-hour',
        'water-per-hour',
        'carbs-per-gel'
    ];

    // Setup integer inputs
    integerInputs.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            setupIntegerInput(element);
        }
    });

    // Setup decimal inputs
    decimalInputs.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            setupDecimalInput(element);
        }
    });
}

// Migration modal for local plans
async function showLocalMigrationModal() {
    try {
        const response = await fetch('/api/auth/list-local-plans');
        const data = await response.json();
        
        if (!response.ok || !data.plans || data.plans.length === 0) {
            authManager.showNotification('No local plans found to migrate', 'info');
            return;
        }
        
        // Store plans for migration
        authManager.localPlansToMigrate = data.plans;
        
        // Show migration modal
        const modal = document.getElementById('migration-modal');
        const plansList = document.getElementById('migration-plans-list');
        
        if (!modal || !plansList) return;
        
        // Update modal title and description for local migration
        const title = modal.querySelector('h2');
        const infoText = modal.querySelector('.info-text');
        if (title) title.textContent = 'Import Local Plans to Your Account';
        if (infoText) infoText.textContent = 'Select which local plans to import into your cloud account. Selected plans will be moved from local storage to your account.';
        
        // Clear previous content
        plansList.innerHTML = '';
        
        // Add select all checkbox
        const selectAllDiv = document.createElement('div');
        selectAllDiv.className = 'migration-select-all';
        selectAllDiv.innerHTML = `
            <input type="checkbox" id="migration-select-all" checked />
            <label for="migration-select-all">Select All</label>
        `;
        plansList.appendChild(selectAllDiv);
        
        // Add plan items
        data.plans.forEach(plan => {
            const planDiv = document.createElement('div');
            planDiv.className = 'migration-plan-item';
            planDiv.innerHTML = `
                <input type="checkbox" class="migration-plan-checkbox" data-filename="${plan.id}" checked />
                <div class="migration-plan-info">
                    <div class="migration-plan-name">${plan.name}</div>
                    <div class="migration-plan-date">Last updated: ${formatTimestampToLocal(plan.updated_at)}</div>
                </div>
            `;
            plansList.appendChild(planDiv);
        });
        
        // Set up select all functionality
        const selectAllCheckbox = document.getElementById('migration-select-all');
        const planCheckboxes = document.querySelectorAll('.migration-plan-checkbox');
        
        selectAllCheckbox.addEventListener('change', (e) => {
            planCheckboxes.forEach(cb => cb.checked = e.target.checked);
        });
        
        // Update select all when individual checkboxes change
        planCheckboxes.forEach(cb => {
            cb.addEventListener('change', () => {
                const allChecked = Array.from(planCheckboxes).every(checkbox => checkbox.checked);
                selectAllCheckbox.checked = allChecked;
            });
        });
        
        // Override import button handler for local migration
        const importBtn = document.getElementById('migration-import-btn');
        const skipBtn = document.getElementById('migration-skip-btn');
        
        // Remove old handlers
        const newImportBtn = importBtn.cloneNode(true);
        importBtn.parentNode.replaceChild(newImportBtn, importBtn);
        const newSkipBtn = skipBtn.cloneNode(true);
        skipBtn.parentNode.replaceChild(newSkipBtn, skipBtn);
        
        newImportBtn.addEventListener('click', async () => {
            await performLocalMigration();
        });
        
        newSkipBtn.addEventListener('click', () => {
            modal.style.display = 'none';
        });
        
        // Show modal
        modal.style.display = 'flex';
    } catch (error) {
        console.error('Error showing migration modal:', error);
        authManager.showNotification('Failed to load local plans', 'error');
    }
}

async function performLocalMigration() {
    const selectedCheckboxes = document.querySelectorAll('.migration-plan-checkbox:checked');
    const selectedFilenames = Array.from(selectedCheckboxes).map(cb => cb.dataset.filename);
    
    if (selectedFilenames.length === 0) {
        document.getElementById('migration-modal').style.display = 'none';
        return;
    }
    
    try {
        const session = await authManager.supabase.auth.getSession();
        if (!session?.data?.session?.access_token) {
            authManager.showNotification('Please sign in to migrate plans', 'error');
            return;
        }
        
        let successCount = 0;
        let errorCount = 0;
        
        // Migrate each selected plan
        for (const filename of selectedFilenames) {
            try {
                const response = await fetch('/api/auth/migrate-local-plan', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${session.data.session.access_token}`
                    },
                    body: JSON.stringify({ filename })
                });
                
                if (response.ok) {
                    successCount++;
                } else {
                    errorCount++;
                    const data = await response.json();
                    console.error(`Failed to migrate ${filename}:`, data.error);
                }
            } catch (error) {
                errorCount++;
                console.error(`Error migrating ${filename}:`, error);
            }
        }
        
        // Hide modal
        document.getElementById('migration-modal').style.display = 'none';
        
        // Show result message
        if (successCount > 0) {
            authManager.showNotification(
                `Successfully imported ${successCount} plan(s) to your account!`, 
                'success'
            );
            // Refresh the plans list
            loadSavedPlans();
        }
        
        if (errorCount > 0) {
            authManager.showNotification(
                `Failed to import ${errorCount} plan(s). Please try again.`, 
                'error'
            );
        }
    } catch (error) {
        console.error('Migration error:', error);
        authManager.showNotification('Failed to import plans. Please try again.', 'error');
    }
}

// Known Races functionality
let allKnownRaces = [];

async function showKnownRaceModal() {
    console.log('=== showKnownRaceModal called ===');
    try {
        console.log('Fetching known races list from API...');
        // Fetch known races from API
        const response = await fetch('/api/list-known-races');
        console.log('Response status:', response.status, response.ok);
        
        const data = await response.json();
        console.log('Known races data:', data);
        
        if (!response.ok) {
            console.error('Response not OK:', data);
            alert('Error loading known races: ' + (data.error || 'Unknown error'));
            return;
        }
        
        allKnownRaces = data.races || [];
        console.log('Number of known races loaded:', allKnownRaces.length);
        renderKnownRaces(allKnownRaces);
        
        // Show modal
        console.log('Adding active class to modal...');
        knownRaceModal.classList.add('active');
        console.log('Modal classes:', knownRaceModal.className);
        console.log('=== showKnownRaceModal completed ===');
    } catch (error) {
        console.error('=== ERROR in showKnownRaceModal ===');
        console.error('Error details:', error);
        console.error('Error stack:', error.stack);
        alert('Failed to load known races. Please try again.');
    }
}

function renderKnownRaces(races) {
    console.log('=== renderKnownRaces called ===');
    console.log('Number of races to render:', races.length);
    console.log('knownRacesList element:', knownRacesList);
    
    knownRacesList.innerHTML = '';
    
    if (races.length === 0) {
        console.log('No races to display');
        knownRacesList.innerHTML = '<p style="text-align: center; color: #666;">No known races found.</p>';
        return;
    }
    
    // Group races by organiser
    const grouped = {};
    races.forEach(race => {
        if (!grouped[race.organiser]) {
            grouped[race.organiser] = [];
        }
        grouped[race.organiser].push(race);
    });
    
    console.log('Grouped races by organiser:', Object.keys(grouped));
    
    // Render grouped races
    Object.keys(grouped).sort().forEach(organiser => {
        console.log(`Rendering organiser: ${organiser} with ${grouped[organiser].length} races`);
        
        const organiserDiv = document.createElement('div');
        organiserDiv.className = 'known-race-organiser';
        organiserDiv.style.marginBottom = '20px';
        
        const organiserHeader = document.createElement('h3');
        organiserHeader.textContent = organiser;
        organiserHeader.style.borderBottom = '2px solid #2563eb';
        organiserHeader.style.paddingBottom = '5px';
        organiserHeader.style.marginBottom = '10px';
        organiserDiv.appendChild(organiserHeader);
        
        grouped[organiser].forEach(race => {
            console.log(`  - Rendering race: ${race.race_name} (${race.year})`);
            
            const raceDiv = document.createElement('div');
            raceDiv.className = 'known-race-item';
            raceDiv.style.padding = '10px';
            raceDiv.style.marginBottom = '5px';
            raceDiv.style.backgroundColor = '#f8f9fa';
            raceDiv.style.borderRadius = '5px';
            raceDiv.style.cursor = 'pointer';
            raceDiv.style.transition = 'background-color 0.2s';
            
            raceDiv.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong>${race.race_name}</strong>
                        <span style="color: #666; margin-left: 10px;">${race.year}</span>
                    </div>
                    <button class="btn btn-sm btn-primary" style="padding: 5px 15px; font-size: 14px;">Load</button>
                </div>
            `;
            
            raceDiv.addEventListener('mouseenter', () => {
                raceDiv.style.backgroundColor = '#e9ecef';
            });
            
            raceDiv.addEventListener('mouseleave', () => {
                raceDiv.style.backgroundColor = '#f8f9fa';
            });
            
            const loadButton = raceDiv.querySelector('button');
            loadButton.addEventListener('click', (e) => {
                console.log(`Load button clicked for: ${race.filename}`);
                e.stopPropagation();
                loadKnownRace(race.filename);
            });
            
            organiserDiv.appendChild(raceDiv);
        });
        
        knownRacesList.appendChild(organiserDiv);
    });
}

function filterKnownRaces() {
    const searchTerm = knownRaceSearch.value.toLowerCase();
    
    if (!searchTerm) {
        renderKnownRaces(allKnownRaces);
        return;
    }
    
    const filtered = allKnownRaces.filter(race => {
        return race.race_name.toLowerCase().includes(searchTerm) ||
               race.organiser.toLowerCase().includes(searchTerm) ||
               (race.year && race.year.toString().includes(searchTerm));
    });
    
    renderKnownRaces(filtered);
}

async function loadKnownRace(filename) {
    console.log('=== loadKnownRace called ===');
    console.log('Filename:', filename);
    
    // Clear all inputs and reset state before loading the known race
    // This ensures any previously loaded plan name is cleared from the UI
    clearAllInputs();
    
    try {
        console.log('Fetching known race from API...');
        const response = await fetch(`/api/load-known-race/${filename}`);
        console.log('Response status:', response.status, response.ok);
        
        const data = await response.json();
        console.log('API response data:', data);
        
        if (!response.ok) {
            console.error('Response not OK:', data);
            alert('Error loading race: ' + (data.error || 'Unknown error'));
            return;
        }
        
        console.log('Checking DOM elements...');
        console.log('fileNameDisplay element:', fileNameDisplay);
        console.log('gpxInfoBox element:', gpxInfoBox);
        
        // Update UI with race info
        const displayText = data.metadata ? 
            `${data.metadata.organiser} - ${data.metadata.race_name} (${data.metadata.year})` : 
            filename;
        console.log('Setting fileNameDisplay.textContent to:', displayText);
        fileNameDisplay.textContent = displayText;
        console.log('fileNameDisplay.textContent is now:', fileNameDisplay.textContent);
        
        const infoHtml = `
            <strong>Distance:</strong> ${data.total_distance} km (${data.total_distance_miles} miles)<br>
            <strong>Elevation Gain:</strong> ${data.total_elev_gain} m<br>
            <strong>Elevation Loss:</strong> ${data.total_elev_loss} m<br>
            <strong>Trackpoints:</strong> ${data.num_trackpoints}
        `;
        console.log('Setting gpxInfoBox.innerHTML to:', infoHtml);
        gpxInfoBox.innerHTML = infoHtml;
        console.log('Setting gpxInfoBox.style.display to block');
        gpxInfoBox.style.display = 'block';
        console.log('gpxInfoBox.style.display is now:', gpxInfoBox.style.display);
        
        // Store the filename and flag for calculations
        console.log('Storing in currentPlan...');
        console.log('Before - currentPlan.gpx_filename:', currentPlan.gpx_filename);
        console.log('Before - currentPlan.is_known_race:', currentPlan.is_known_race);
        currentPlan.gpx_filename = data.filename;
        currentPlan.is_known_race = data.is_known_race || false;
        currentPlan.total_distance = data.total_distance;
        console.log('After - currentPlan.gpx_filename:', currentPlan.gpx_filename);
        console.log('After - currentPlan.is_known_race:', currentPlan.is_known_race);
        
        // Clear checkpoint distances and reset inputs
        console.log('Clearing checkpoint distances and regenerating inputs...');
        currentPlan.checkpoint_distances = [];
        generateCheckpointInputs();
        
        // Update summary cards for distance and elevation gain immediately
        document.getElementById('summary-distance').textContent = `${data.total_distance} km`;
        document.getElementById('summary-elev-gain').textContent = `+${data.total_elev_gain} m`;
        
        // Fetch elevation profile for vertical plot (basic, no segments yet)
        console.log('Fetching elevation profile...');
        try {
            const profileResponse = await fetch('/api/calculate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    gpx_filename: data.filename,
                    is_known_race: data.is_known_race || false,
                    checkpoint_distances: [],
                    checkpoint_dropbags: [],
                    segment_terrain_types: ['smooth_trail'],
                    avg_cp_time: 5,
                    z2_pace: 6.5,
                    climbing_ability: 'moderate',
                    carbs_per_hour: 60,
                    water_per_hour: 500,
                    fatigue_enabled: true,
                    fitness_level: 'recreational',
                    skill_level: 0.5
                })
            });
            const profileData = await profileResponse.json();
            console.log('Elevation profile response:', profileResponse.ok, profileData);
            
            if (profileResponse.ok && profileData.elevation_profile && profileData.elevation_profile.length > 0) {
                console.log('Rendering elevation chart...');
                // Render the vertical profile with a dummy segments array (just Start→Finish)
                renderElevationChart(profileData.elevation_profile, [
                    { from: 'Start', to: 'Finish', distance: data.total_distance }
                ]);
                // Show the results container and hide the placeholder
                resultsContainer.style.display = 'block';
                noResults.style.display = 'none';
                console.log('Elevation chart rendered successfully');
            } else {
                console.error('Failed to get elevation profile:', profileData);
            }
        } catch (e) {
            console.error('Error fetching elevation profile:', e);
            // Fail silently if profile can't be rendered
        }
        
        // Clear search
        console.log('Clearing search field...');
        knownRaceSearch.value = '';
        
        // Show success message first, then close modal after user acknowledges
        console.log('Showing success alert...');
        alert('Known race loaded successfully! You can now configure checkpoints and calculate your race plan.');
        
        // Hide modal after alert is acknowledged
        console.log('Hiding modal...');
        hideModal(knownRaceModal);
        console.log('=== loadKnownRace completed successfully ===');
    } catch (error) {
        console.error('=== ERROR in loadKnownRace ===');
        console.error('Error details:', error);
        console.error('Error stack:', error.stack);
        alert('Failed to load known race. Please try again.');
    }
}

// Initialize input filtering when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    setupNumericInputFiltering();
    generateCheckpointInputs();
    validateCheckpointDistances();
});
