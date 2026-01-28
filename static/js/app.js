// State management
let currentPlan = {
    gpx_filename: null,
    checkpoint_distances: [],
    segment_terrain_types: [],
    segments: null,
    summary: null,
    elevation_profile: null,
    loadedFilename: null  // Track the currently loaded plan filename
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
const saveAsBtn = document.getElementById('save-as-btn');
const saveCancelBtn = document.getElementById('save-cancel-btn');
const loadCancelBtn = document.getElementById('load-cancel-btn');
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

// Event Listeners
gpxFileInput.addEventListener('change', handleGPXUpload);
numCheckpointsInput.addEventListener('change', generateCheckpointInputs);
calculateBtn.addEventListener('click', calculateRacePlan);
saveBtn.addEventListener('click', showSaveModal);
loadBtn.addEventListener('click', showLoadModal);
exportBtn.addEventListener('click', exportToCSV);
clearBtn.addEventListener('click', clearAll);
saveConfirmBtn.addEventListener('click', () => savePlan(false));
saveAsBtn.addEventListener('click', () => savePlan(true));
saveCancelBtn.addEventListener('click', () => hideModal(saveModal));
loadCancelBtn.addEventListener('click', () => hideModal(loadModal));

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

// Initialize
generateCheckpointInputs();

// Functions
function renderElevationChart(elevationProfile, segments) {
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
                waterToNext: waterToNext
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
                            
                            if (nearCheckpoint) {
                                return [
                                    `${nearCheckpoint.label}`,
                                    `Distance: ${nearCheckpoint.distance.toFixed(1)} km`
                                ];
                            }
                            
                            return `Distance: ${distance} km`;
                        },
                        label: (context) => {
                            const distance = parseFloat(context.label);
                            const labels = [`Elevation: ${context.parsed.y.toFixed(0)} m`];
                            
                            // Check if we're near a checkpoint
                            const nearCheckpoint = checkpointData.find(cp => 
                                Math.abs(cp.distance - distance) < 0.5
                            );
                            
                            if (nearCheckpoint) {
                                labels.push('');
                                labels.push(`Next Section: ${nearCheckpoint.distanceToNext.toFixed(1)} km`);
                                labels.push(`Fuel Needed: ${nearCheckpoint.carbsToNext}g carbs`);
                                labels.push(`Hydration: ${nearCheckpoint.waterToNext}L water`);
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

function clearAll() {
    if (!confirm('Are you sure you want to clear all data and start again?')) {
        return;
    }
    
    // Reset state
    currentPlan = {
        gpx_filename: null,
        checkpoint_distances: [],
        segment_difficulties: [],
        segments: null,
        summary: null,
        elevation_profile: null,
        loadedFilename: null  // Clear loaded filename
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
    document.getElementById('climbing-ability').value = 'moderate';
    document.getElementById('carbs-per-hour').value = 60;
    document.getElementById('water-per-hour').value = 500;
    document.getElementById('race-start-time').value = '';
    document.getElementById('fatigue-enabled').checked = true;
    document.getElementById('fitness-level').value = 'recreational';
    document.getElementById('fitness-level').disabled = false;
    document.getElementById('terrain-enabled').checked = false;
    document.getElementById('skill-level').value = 0.5;
    document.getElementById('default-terrain-type').value = '';
    terrainSkillContainer.style.display = 'none';
    
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
            currentPlan.loadedFilename = null;  // Clear loaded filename when uploading new GPX
            
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

    // Create only checkpoint distance inputs
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
    const z2PaceMin = parseFloat(document.getElementById('z2-pace-min').value) || 6;
    const z2PaceSec = parseFloat(document.getElementById('z2-pace-sec').value) || 30;
    const z2Pace = z2PaceMin + z2PaceSec / 60;
    const climbingAbility = document.getElementById('climbing-ability').value || 'moderate';
    const carbsPerHour = parseFloat(document.getElementById('carbs-per-hour').value) || 60;
    const waterPerHour = parseFloat(document.getElementById('water-per-hour').value) || 500;
    const raceStartTime = document.getElementById('race-start-time').value || null;
    const fatigueEnabled = document.getElementById('fatigue-enabled').checked;
    const fitnessLevel = document.getElementById('fitness-level').value;
    const skillLevel = parseFloat(document.getElementById('skill-level').value) || 0.5;

    const requestData = {
        gpx_filename: currentPlan.gpx_filename,
        checkpoint_distances: currentPlan.checkpoint_distances,
        segment_terrain_types: currentPlan.segment_terrain_types,
        avg_cp_time: avgCpTime,
        z2_pace: z2Pace,
        climbing_ability: climbingAbility,
        carbs_per_hour: carbsPerHour,
        water_per_hour: waterPerHour,
        race_start_time: raceStartTime,
        fatigue_enabled: fatigueEnabled,
        fitness_level: fitnessLevel,
        skill_level: skillLevel
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
    document.getElementById('summary-cp-time').textContent = summary.total_cp_time_str;
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
        const paceStyle = seg.pace_capped ? 'color: #ef4444; font-weight: bold;' : 'font-weight: bold;';
        const timeOfArrival = seg.time_of_day ? `${seg.time_of_day} at ${seg.to}` : '--';
        
        // Format terrain type for display
        const terrainTypeDisplay = seg.terrain_type ? seg.terrain_type.replace(/_/g, ' ') : 'smooth trail';
        const terrainFactorDisplay = seg.terrain_factor ? `${seg.terrain_factor.toFixed(2)}x` : '1.00x';
        
        row.innerHTML = `
            <td><strong>${seg.from} → ${seg.to}</strong></td>
            <td>${seg.distance}</td>
            <td>+${seg.elev_gain}/-${seg.elev_loss}</td>
            <td>${seg.net_elev > 0 ? '+' : ''}${seg.net_elev}</td>
            <td>${seg.elev_pace_str}</td>
            <td class="fatigue-col" style="display: ${hasFatigue ? 'table-cell' : 'none'}">${seg.fatigue_str}</td>
            <td class="terrain-col" style="display: ${terrainEnabled ? 'table-cell' : 'none'}">${terrainFactorDisplay}</td>
            <td><strong style="${paceStyle}">${seg.pace_str}</strong></td>
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

    // When using Save As, check if a plan with this name already exists
    if (forceSaveAs) {
        try {
            const listResponse = await fetch('/api/list-plans');
            const listData = await listResponse.json();
            
            if (listResponse.ok) {
                // Check if any existing plan has the same name
                const existingPlan = listData.plans.find(plan => plan.name === planName);
                
                if (existingPlan) {
                    alert('A plan with this name already exists. Please choose a different name.');
                    return;  // Keep modal open so user can rename
                }
            }
        } catch (error) {
            console.error('Error checking existing plans:', error);
            // Continue with save attempt even if check fails
        }
    }

    const saveData = {
        plan_name: planName,
        gpx_filename: currentPlan.gpx_filename,
        checkpoint_distances: currentPlan.checkpoint_distances,
        segment_terrain_types: currentPlan.segment_terrain_types,
        avg_cp_time: parseFloat(document.getElementById('avg-cp-time').value),
        z2_pace: parseFloat(document.getElementById('z2-pace-min').value) + parseFloat(document.getElementById('z2-pace-sec').value) / 60,
        climbing_ability: document.getElementById('climbing-ability').value,
        carbs_per_hour: parseFloat(document.getElementById('carbs-per-hour').value),
        water_per_hour: parseFloat(document.getElementById('water-per-hour').value),
        race_start_time: document.getElementById('race-start-time').value || null,
        fatigue_enabled: document.getElementById('fatigue-enabled').checked,
        fitness_level: document.getElementById('fitness-level').value,
        skill_level: parseFloat(document.getElementById('skill-level').value),
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
            // Determine if this was an update or a new save
            const wasUpdate = !forceSaveAs && currentPlan.loadedFilename;
            
            // Always update to the filename returned by the server
            currentPlan.loadedFilename = data.filename;
            
            // Show appropriate message based on operation
            if (wasUpdate) {
                alert('Plan updated successfully!');
            } else {
                alert('Plan saved successfully!');
            }
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
            // Track the loaded filename for save/save-as functionality
            currentPlan.loadedFilename = filename;
            
            // Load plan data into form
            currentPlan.gpx_filename = data.gpx_filename;
            currentPlan.checkpoint_distances = data.checkpoint_distances || [];
            currentPlan.segment_terrain_types = data.segment_terrain_types || [];
            
            document.getElementById('num-checkpoints').value = currentPlan.checkpoint_distances.length;
            document.getElementById('avg-cp-time').value = data.avg_cp_time || 5;
            
            const z2Pace = data.z2_pace || 6.5;
            document.getElementById('z2-pace-min').value = Math.floor(z2Pace);
            document.getElementById('z2-pace-sec').value = Math.round((z2Pace % 1) * 60);
            
            document.getElementById('climbing-ability').value = data.climbing_ability || 'moderate';
            document.getElementById('carbs-per-hour').value = data.carbs_per_hour || 60;
            document.getElementById('water-per-hour').value = data.water_per_hour || 500;
            document.getElementById('race-start-time').value = data.race_start_time || '';
            document.getElementById('fatigue-enabled').checked = data.fatigue_enabled !== undefined ? data.fatigue_enabled : true;
            document.getElementById('fitness-level').value = data.fitness_level || 'recreational';
            document.getElementById('fitness-level').disabled = !document.getElementById('fatigue-enabled').checked;
            
            // Load terrain settings
            const hasTerrainTypes = data.segment_terrain_types && data.segment_terrain_types.some(t => t !== 'smooth_trail');
            document.getElementById('terrain-enabled').checked = hasTerrainTypes;
            document.getElementById('skill-level').value = data.skill_level || 0.5;
            terrainSkillContainer.style.display = hasTerrainTypes ? 'block' : 'none';

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
