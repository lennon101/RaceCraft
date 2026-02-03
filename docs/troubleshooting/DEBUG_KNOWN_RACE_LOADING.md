# Debug Logging for Known Race Loading

## Problem Report

User reported: "Loading a known race still does not update the page to show the loaded known race."

## Solution: Added Debug Logging

Added comprehensive `console.log()` statements throughout the known race loading flow to identify where the issue was occurring.

## Debug Logging Added

### 1. `showKnownRaceModal()` Function

Logs when the modal is opened and races are fetched:
```javascript
=== showKnownRaceModal called ===
Fetching known races list from API...
Response status: 200 true
Known races data: {grouped: Object, races: Array(6)}
Number of known races loaded: 6
Adding active class to modal...
Modal classes: modal active
=== showKnownRaceModal completed ===
```

### 2. `renderKnownRaces()` Function

Logs the rendering process:
```javascript
=== renderKnownRaces called ===
Number of races to render: 6
Grouped races by organiser: [UTMB, Ironman, Salomon]
Rendering organiser: UTMB with 4 races
  - Rendering race: Mont Blanc 100 (2024)
  - Rendering race: CCC (2023)
  ...
```

### 3. `loadKnownRace()` Function

Logs the complete loading process:
```javascript
=== loadKnownRace called ===
Filename: UTMB-Mont_Blanc_100-2024.gpx
Fetching known race from API...
Response status: 200 true
API response data: {...}
Checking DOM elements...
fileNameDisplay element: JSHandle@node
gpxInfoBox element: JSHandle@node
Setting fileNameDisplay.textContent to: UTMB - Mont Blanc 100 (2024)
fileNameDisplay.textContent is now: UTMB - Mont Blanc 100 (2024)
Setting gpxInfoBox.innerHTML to: ...
Setting gpxInfoBox.style.display to block
gpxInfoBox.style.display is now: block
Storing in currentPlan...
Before - currentPlan.gpx_filename: null
Before - currentPlan.is_known_race: undefined
After - currentPlan.gpx_filename: UTMB-Mont_Blanc_100-2024.gpx
After - currentPlan.is_known_race: true
Clearing checkpoint distances and regenerating inputs...
Clearing search field...
Showing success alert...
Hiding modal...
=== loadKnownRace completed successfully ===
```

## What the Debug Logging Revealed

### Initial Problem (Before Fix)
The debug logs showed:
```javascript
Known races data: {grouped: Object, races: Array(0)}
Number of known races loaded: 0
No races to display
```

**Root Cause**: The API returned 0 races because the GPX files were in the wrong directory:
- Files were in: `data/known_races/`
- App was looking in: `FuelPlanData/known_races/` (for local development)

### After Fix
Once the GPX files were copied to the correct location, the debug logs showed:
```javascript
Known races data: {grouped: Object, races: Array(6)}
Number of known races loaded: 6
```

And when loading a race:
```javascript
Setting fileNameDisplay.textContent to: UTMB - Mont Blanc 100 (2024)
fileNameDisplay.textContent is now: UTMB - Mont Blanc 100 (2024)
```

This confirmed that:
1. ✅ API successfully returned race data
2. ✅ DOM elements were correctly updated
3. ✅ currentPlan state was properly set
4. ✅ Modal closed successfully
5. ✅ Page displayed the loaded race information

## Test Results

**Functionality Verified:**
- ✅ Modal opens and displays races
- ✅ Races are grouped by organiser
- ✅ Clicking "Load" fetches race data from API
- ✅ Page updates to show race name and details
- ✅ GPX info box displays distance, elevation, trackpoints
- ✅ currentPlan state is updated with filename and flag
- ✅ Checkpoint inputs are cleared and ready
- ✅ Modal closes after loading

**Final State:**
- File name display: "UTMB - Mont Blanc 100 (2024)"
- GPX info shown: Distance 3.88 km, Elevation Gain 915 m, etc.
- No errors in console
- All functionality working as expected

## Benefits of Debug Logging

1. **Quick Problem Identification**: Immediately identified that no races were being loaded
2. **API Verification**: Confirmed API responses were correct
3. **DOM Update Tracking**: Verified each UI element was being updated
4. **State Management**: Showed currentPlan was being set correctly
5. **Flow Visibility**: Clear view of the entire loading process
6. **Future Debugging**: Will help identify any future issues quickly

## Recommendation

Keep the debug logging in place (or controlled by a debug flag) as it provides valuable insight into the application flow and makes troubleshooting much easier for both developers and users reporting issues.
