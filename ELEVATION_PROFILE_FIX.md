# Elevation Profile X-Axis Fix - Implementation Details

## Problem Summary
The elevation profile x-axis was using array indices instead of actual cumulative distance, causing visual distortion where:
- Dense GPX sampling sections stretched the plot
- Sparse GPX sampling sections compressed the plot
- On a 102 km route, the 50 km point appeared only ~25% across the plot

## Solution Overview
Changed Chart.js configuration to use a linear distance-based scale instead of categorical index-based labels.

## Code Changes

### 1. Data Format Change
**File:** `static/js/app.js` (Lines 486-488)

**BEFORE (Index-based):**
```javascript
data: {
    labels: elevationProfile.map(p => p.distance.toFixed(1)),  // Distance as labels
    datasets: [{
        label: 'Elevation (m)',
        data: elevationProfile.map(p => p.elevation),           // Elevation at indices 0,1,2,3...
        // ...
    }]
}
```

**AFTER (Distance-based):**
```javascript
data: {
    datasets: [{
        label: 'Elevation (m)',
        data: elevationProfile.map(p => ({ x: p.distance, y: p.elevation })),  // x=distance, y=elevation
        // ...
    }]
}
```

**Impact:** Chart.js now plots points at their true distance values on the x-axis instead of sequential array indices.

---

### 2. X-Axis Scale Configuration
**File:** `static/js/app.js` (Lines 618-644)

**BEFORE (Categorical/Index scale):**
```javascript
x: {
    title: {
        display: true,
        text: 'Distance (km)',
        // ...
    },
    ticks: {
        maxTicksLimit: 15,
        callback: function(value, index) {
            // Show every nth tick based on array length
            const step = Math.ceil(elevationProfile.length / 15);
            return index % step === 0 ? this.getLabelForValue(value) : '';
        }
    },
    // ...
}
```

**AFTER (Linear distance scale):**
```javascript
x: {
    type: 'linear',  // Force linear scale based on numeric x values
    min: 0,          // Start at 0 km
    max: elevationProfile[elevationProfile.length - 1].distance,  // End at total distance
    title: {
        display: true,
        text: 'Distance (km)',
        // ...
    },
    ticks: {
        callback: function(value) {
            return value.toFixed(1);  // Format distance values
        },
        autoSkip: true,
        maxTicksLimit: 15,
        stepSize: (function() {
            // Calculate dynamic step size based on total distance
            const totalDistance = elevationProfile[elevationProfile.length - 1].distance;
            
            // Determine appropriate step size
            if (totalDistance <= 10) return 1;
            if (totalDistance <= 30) return 2;
            if (totalDistance <= 50) return 5;
            if (totalDistance <= 100) return 10;
            if (totalDistance <= 200) return 20;
            return 25;
        })()
    },
    // ...
}
```

**Impact:**
- `type: 'linear'` ensures proportional distance representation
- `min: 0` and `max: totalDistance` bounds the x-axis to the exact race distance (no whitespace)
- Dynamic `stepSize` adapts to route distance (1-25 km intervals)
- Tick labels show actual distance values, not array indices
- `autoSkip: true` automatically adjusts tick density based on plot width

---

### 3. Checkpoint Line Positioning
**File:** `static/js/app.js` (Lines 458-459)

**BEFORE (Find array index, use index for positioning):**
```javascript
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
    
    // Draw checkpoint line...
});
```

**AFTER (Use distance value directly):**
```javascript
checkpointData.forEach(cp => {
    // Get pixel position using the distance value directly
    const xPos = x.getPixelForValue(cp.distance);
    
    // Draw checkpoint line...
});
```

**Impact:**
- Simplified from 15 lines to 1 line
- Checkpoint lines now align perfectly with their true distance positions
- No more approximation errors from finding closest array index

---

### 4. Tooltip Updates
**File:** `static/js/app.js` (Lines 514, 529)

**BEFORE (Parse label string):**
```javascript
callbacks: {
    title: (context) => {
        const distance = parseFloat(context[0].label);  // Parse label string
        // ...
    },
    label: (context) => {
        const distance = parseFloat(context.label);     // Parse label string
        // ...
    }
}
```

**AFTER (Read from coordinate data):**
```javascript
callbacks: {
    title: (context) => {
        const distance = context[0].parsed.x;           // Read x coordinate
        // ...
    },
    label: (context) => {
        const distance = context.parsed.x;              // Read x coordinate
        // ...
    }
}
```

**Impact:**
- More direct access to distance values
- No string parsing required
- More accurate distance reporting in tooltips

---

## Distance-Based Step Size Table

| Total Distance | Step Size | Approximate Tick Count |
|----------------|-----------|------------------------|
| ≤ 10 km        | 1 km      | ~10 ticks              |
| ≤ 30 km        | 2 km      | ~15 ticks              |
| ≤ 50 km        | 5 km      | ~10 ticks              |
| ≤ 100 km       | 10 km     | ~10 ticks              |
| ≤ 200 km       | 20 km     | ~10 ticks              |
| > 200 km       | 25 km     | ~10+ ticks             |

---

## Expected Behavior Changes

### Before Fix
- X-axis positions based on array indices: 0, 1, 2, 3, 4, 5, ...
- Distance labels displayed at these positions (misleading)
- Denser GPX sampling → more points → visual stretching
- Sparser GPX sampling → fewer points → visual compression
- Example: On 102 km route with 500 sampled points:
  - Point at index 125 (25% through array) might be at 50 km distance
  - Appears at 25% across plot, but should be at ~49% (50/102)

### After Fix
- X-axis positions based on true distance: 0.0, 10.5, 21.3, 33.7, 50.2, ...
- Distance values displayed at their actual positions
- GPX sampling density has no effect on visual representation
- Checkpoint lines align with true distance positions
- Example: On 102 km route:
  - Point at 50 km distance appears at ~49% across plot (50/102) ✓
  - Point at 75 km distance appears at ~74% across plot (75/102) ✓

---

## Testing

Run the validation test:
```bash
python test_elevation_profile_fix.py
```

Expected output:
```
✓ ALL TESTS PASSED - Changes look correct!

Expected Benefits:
  • X-axis represents cumulative distance linearly
  • Graticules evenly spaced and adapt to total distance
  • Visual distortion from GPX sampling eliminated
  • On 102km route, 50km point appears at ~50% (not ~25%)
```

---

## Related Files
- `static/js/app.js` - Main implementation
- `test_elevation_profile_fix.py` - Validation test
- `FATIGUE_MODEL.md` - Fatigue model documentation
- `CLIMBING_MODEL.md` - Climbing model documentation
- `TERRAIN_DIFFICULTY.md` - Terrain difficulty documentation

---

## Chart.js Documentation References
- [Chart.js Linear Scale](https://www.chartjs.org/docs/latest/axes/cartesian/linear.html)
- [Chart.js Data Structures](https://www.chartjs.org/docs/latest/general/data-structures.html)
- [Chart.js Tick Configuration](https://www.chartjs.org/docs/latest/axes/cartesian/#tick-configuration)
