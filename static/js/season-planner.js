// Season Planner JavaScript

let races = [];
let trainingChart = null;

// Initialize the page
document.addEventListener('DOMContentLoaded', () => {
    initializePage();
    setupEventListeners();
    addRace(); // Add first race by default
});

function initializePage() {
    // Update unit display when training unit changes
    const trainingUnitSelect = document.getElementById('training-unit');
    const baseLoadUnit = document.getElementById('base-load-unit');
    
    trainingUnitSelect.addEventListener('change', (e) => {
        baseLoadUnit.textContent = e.target.value;
    });
}

function setupEventListeners() {
    document.getElementById('add-race-btn').addEventListener('click', addRace);
    document.getElementById('calculate-season-btn').addEventListener('click', calculateSeason);
}

function addRace() {
    const raceId = Date.now();
    const racesContainer = document.getElementById('races-container');
    const currentUnit = document.getElementById('training-unit').value;
    
    const raceEntry = document.createElement('div');
    raceEntry.className = 'race-entry';
    raceEntry.dataset.raceId = raceId;
    
    raceEntry.innerHTML = `
        <div class="race-entry-header">
            <h4>Race ${races.length + 1}</h4>
            <button class="remove-race-btn" onclick="removeRace(${raceId})">
                <span class="mdi mdi-close"></span>
            </button>
        </div>
        <div class="race-inputs">
            <div class="input-group">
                <label>Race Name:</label>
                <input type="text" class="race-name" placeholder="e.g., Spring Marathon" required />
            </div>
            <div class="input-group">
                <label>Race Date:</label>
                <input type="date" class="race-date" required />
            </div>
            <div class="input-group">
                <label>
                    Peak Weekly Load:
                    <span class="info-icon mdi mdi-information-outline" 
                          tabindex="0"
                          data-tooltip="Target training volume you want to achieve before this race."></span>
                </label>
                <input type="number" class="peak-load" min="20" max="500" placeholder="100" step="5" required />
                <span class="unit" id="peak-unit-${raceId}">${currentUnit}</span>
            </div>
        </div>
    `;
    
    racesContainer.appendChild(raceEntry);
    races.push(raceId);
    
    // Enable tooltips for the new race entry
    enableTooltips(raceEntry);
}

function removeRace(raceId) {
    const raceEntry = document.querySelector(`[data-race-id="${raceId}"]`);
    if (raceEntry) {
        raceEntry.remove();
        races = races.filter(id => id !== raceId);
        
        // Update race numbers
        const allRaces = document.querySelectorAll('.race-entry');
        allRaces.forEach((entry, index) => {
            const header = entry.querySelector('.race-entry-header h4');
            if (header) {
                header.textContent = `Race ${index + 1}`;
            }
        });
    }
}

function enableTooltips(container) {
    const tooltips = container.querySelectorAll('.info-icon');
    tooltips.forEach(icon => {
        icon.addEventListener('mouseenter', showTooltip);
        icon.addEventListener('mouseleave', hideTooltip);
        icon.addEventListener('focus', showTooltip);
        icon.addEventListener('blur', hideTooltip);
    });
}

function showTooltip(e) {
    const tooltipText = e.target.dataset.tooltip;
    if (!tooltipText) return;
    
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.textContent = tooltipText;
    tooltip.style.position = 'absolute';
    tooltip.style.zIndex = '1000';
    
    document.body.appendChild(tooltip);
    
    const rect = e.target.getBoundingClientRect();
    tooltip.style.top = `${rect.bottom + 5}px`;
    tooltip.style.left = `${rect.left}px`;
    
    e.target._tooltip = tooltip;
}

function hideTooltip(e) {
    if (e.target._tooltip) {
        e.target._tooltip.remove();
        delete e.target._tooltip;
    }
}

async function calculateSeason() {
    // Collect race data
    const raceEntries = document.querySelectorAll('.race-entry');
    const racesData = [];
    
    for (const entry of raceEntries) {
        const name = entry.querySelector('.race-name').value;
        const date = entry.querySelector('.race-date').value;
        const peakLoad = parseFloat(entry.querySelector('.peak-load').value);
        
        if (!name || !date || !peakLoad) {
            alert('Please fill in all race details');
            return;
        }
        
        racesData.push({ name, date, peakLoad });
    }
    
    if (racesData.length === 0) {
        alert('Please add at least one race');
        return;
    }
    
    // Sort races by date
    racesData.sort((a, b) => new Date(a.date) - new Date(b.date));
    
    // Collect training settings
    const trainingSettings = {
        unit: document.getElementById('training-unit').value,
        blockLength: parseInt(document.getElementById('block-length').value),
        baseLoad: parseFloat(document.getElementById('base-load').value),
        recoveryPercentage: parseFloat(document.getElementById('recovery-percentage').value),
        taperWeeks: parseInt(document.getElementById('taper-weeks').value)
    };
    
    // Send to backend for calculation
    try {
        const response = await fetch('/api/season-planner/calculate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                races: racesData,
                settings: trainingSettings
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to calculate training plan');
        }
        
        const result = await response.json();
        displayResults(result);
    } catch (error) {
        console.error('Error calculating season:', error);
        alert(`Error: ${error.message}`);
    }
}

function displayResults(result) {
    // Hide placeholder
    document.getElementById('schedule-results').style.display = 'none';
    
    // Try to show and populate chart (if Chart.js is available)
    if (typeof Chart !== 'undefined') {
        document.getElementById('chart-container').style.display = 'block';
        try {
            renderChart(result.schedule, result.settings.unit);
        } catch (error) {
            console.warn('Failed to render chart:', error);
            document.getElementById('chart-container').style.display = 'none';
        }
    }
    
    // Show and populate table (always works)
    document.getElementById('schedule-table-container').style.display = 'block';
    renderTable(result.schedule, result.settings.unit);
}

function renderChart(schedule, unit) {
    if (typeof Chart === 'undefined') {
        console.warn('Chart.js not loaded, skipping chart rendering');
        return;
    }
    
    const ctx = document.getElementById('training-chart');
    
    if (trainingChart) {
        trainingChart.destroy();
    }
    
    const labels = schedule.map(week => `Week ${week.weekNumber}`);
    const data = schedule.map(week => week.load);
    const colors = schedule.map(week => {
        switch (week.type) {
            case 'race': return 'rgba(239, 68, 68, 0.8)';
            case 'taper': return 'rgba(245, 158, 11, 0.8)';
            case 'recovery': return 'rgba(16, 185, 129, 0.8)';
            default: return 'rgba(37, 99, 235, 0.8)';
        }
    });
    
    trainingChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: `Training Load (${unit})`,
                data: data,
                backgroundColor: colors,
                borderColor: colors.map(c => c.replace('0.8', '1')),
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: true
                },
                title: {
                    display: true,
                    text: 'Training Schedule Overview'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: `Weekly Load (${unit})`
                    }
                }
            }
        }
    });
}

function renderTable(schedule, unit) {
    const tbody = document.getElementById('schedule-tbody');
    tbody.innerHTML = '';
    
    schedule.forEach(week => {
        const row = document.createElement('tr');
        
        const typeClass = `week-type-${week.type}`;
        const typeLabel = week.type.charAt(0).toUpperCase() + week.type.slice(1);
        
        row.innerHTML = `
            <td>${week.weekNumber}</td>
            <td>${formatDate(week.startDate)}</td>
            <td>${week.load} ${unit}</td>
            <td><span class="${typeClass}">${typeLabel}</span></td>
            <td>${week.notes || ''}</td>
        `;
        
        tbody.appendChild(row);
    });
}

function formatDate(dateString) {
    const date = new Date(dateString);
    const options = { month: 'short', day: 'numeric', year: 'numeric' };
    return date.toLocaleDateString('en-US', options);
}
