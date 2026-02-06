# Graceful Handling of Missing Values in JSON Race Plans

## Overview
As of version 1.6.x, RaceCraft now gracefully handles missing or incomplete fields when importing or loading JSON race plan files. This ensures backward compatibility with older exported plans and prevents import errors due to missing data.

## Problem
Previously, importing older or incomplete JSON race plan files could result in errors such as:
```
Error importing plan: Can't find variable: exportImportModal
```

This occurred when:
- Expected fields were missing from the JSON file
- JSON files were exported from older versions of RaceCraft
- Users manually edited JSON files and removed fields
- Null values were present where arrays were expected

## Solution
RaceCraft now automatically applies default values for any missing fields during import or load operations. This happens at two levels:

### Backend (Python - app.py)
The `/api/import-plan` endpoint includes an `apply_plan_defaults()` function that ensures all required fields have sensible default values before returning data to the frontend.

### Frontend (JavaScript - app.js)
The `applyDefaultValues()` helper function in the frontend ensures consistent handling of missing fields in both the `loadPlan()` and `handleImportPlan()` functions.

## Default Values
The following default values are applied when fields are missing:

### Core Plan Configuration
- `plan_name`: `null`
- `gpx_filename`: `null`
- `checkpoint_distances`: `[]` (empty array)
- `checkpoint_dropbags`: `[]` (empty array)
- `segment_terrain_types`: `[]` (empty array)

### Athlete Configuration
- `avg_cp_time`: `5` (minutes)
- `z2_pace`: `6.5` (min/km)
- `climbing_ability`: `'moderate'`
- `carbs_per_hour`: `60` (grams)
- `water_per_hour`: `500` (ml)
- `carbs_per_gel`: `null` (optional)
- `race_start_time`: `null` (optional)

### Fatigue & Fitness
- `fatigue_enabled`: `true`
- `fitness_level`: `'recreational'`
- `skill_level`: `0.5` (intermediate)

### Calculated Results (Optional)
- `segments`: `null`
- `summary`: `null`
- `elevation_profile`: `null`
- `dropbag_contents`: `null`

### Target Time Mode (Optional)
- `pacing_mode`: `'base_pace'`
- `target_time_hours`: `null`
- `target_time_minutes`: `null`
- `target_time_seconds`: `null`

## Benefits
1. **Backward Compatibility**: Older JSON files from previous versions can be imported without modification
2. **Error Prevention**: No runtime errors from missing fields
3. **User Experience**: Clear, predictable behavior when importing incomplete plans
4. **Flexibility**: Users can manually create minimal JSON files with only required fields
5. **Future-Proof**: New fields added in future versions won't break older exports

## Usage Examples

### Minimal Plan (Only GPX filename)
```json
{
  "gpx_filename": "my_route.gpx"
}
```
All other fields will be populated with defaults.

### Partial Plan (Some fields specified)
```json
{
  "plan_name": "My 100K Race",
  "gpx_filename": "100k_route.gpx",
  "checkpoint_distances": [15, 30, 50, 70],
  "climbing_ability": "strong",
  "carbs_per_hour": 80
}
```
Missing fields like `fitness_level`, `skill_level`, etc. will use defaults.

### Legacy Plan (Old format)
JSON files exported from older versions (before skill_level, target_time_mode, etc. were added) will work seamlessly with defaults applied for new fields.

## Testing
Comprehensive tests are provided in `/tmp/test_json_import.py` to verify:
- Minimal plans with only 1-2 fields
- Partial plans with some fields missing
- Old format plans missing newer fields
- Plans with null values for array fields
- Complete plans with all fields specified

All tests pass successfully, confirming that missing values are handled gracefully.

## Bug Fix
This update also fixes the undefined `exportImportModal` variable bug that caused the error:
```
Error importing plan: Can't find variable: exportImportModal
```

The reference to this non-existent modal has been removed from the `handleImportPlan` function.

## Implementation Details

### Backend Function (app.py)
```python
def apply_plan_defaults(plan_data):
    """Apply default values for missing fields in plan data."""
    # Defines defaults dictionary
    # Merges plan_data with defaults
    # Ensures arrays are always arrays
    # Returns complete plan with all fields
```

### Frontend Function (app.js)
```javascript
function applyDefaultValues(planData) {
    // Defines defaults object
    // Merges planData with defaults
    // Ensures arrays are always arrays
    // Returns complete plan with all fields
}
```

Both functions are called automatically during import/load operations, so users don't need to take any special action.

## Versioning
This feature was added in version 1.6.1 (or later) as part of the effort to improve robustness and backward compatibility.

---

For more information or to report issues, please visit the [RaceCraft GitHub repository](https://github.com/lennon101/RaceCraft).
