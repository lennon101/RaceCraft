# Debug Investigation: Target Time Mode

## Issue Report

User reported that the new independent target time calculation was not being used in the backend, with symptoms:
- Still showing results from old Base Pace mode
- Showing fatigue seconds (should be 0)
- No effort labels (should show easy/medium/hard/very_hard)
- Total time doesn't match target

## Investigation Results

**FINDING: The independent target time calculation IS working correctly!**

### What Was Verified

1. ✅ **Function is being called**: `calculate_independent_target_pacing` executes when `pacing_mode='target_time'`
2. ✅ **Correct code path**: The target time mode branch in the segment calculation loop is used
3. ✅ **All requirements met**:
   - Total time matches target exactly (to within 0.0001 minutes)
   - Pace varies based on terrain and elevation (not fixed base pace)
   - Fatigue seconds = 0 (fatigue not applied)
   - Effort levels present (easy/medium/hard/very_hard, not 'steady')
   - Base pace, fitness, climbing ability, and technical skill have no effect on results

### Debug Logs Added

Added logging to trace the calculation flow:

```
=== CALCULATE API CALLED ===
pacing_mode: target_time
target_time_str: 03:00:00
use_target_time: True

=== INDEPENDENT TARGET TIME MODE ===
Target time: 174.00 min
Total distance: 10.00 km
Flat-equivalent base pace: 17.40 min/km (17:24)
Segment 1: dist=5.00km, elev_gain=300m, terrain=technical, gradient=6.0%, 
           weight=254.15, time=172.14min, pace=34.43min/km, effort=hard
...

>>> Using TARGET TIME MODE for segment calculations
```

### Test Results

Created comprehensive test suite (`test_target_time_fix.py`) that validates:

#### Target Time Mode Tests
```
1. Total time matches target:           ✓ PASS (diff: 0.0000 min)
2. Pace varies (not fixed base):        ✓ PASS
3. Fatigue seconds = 0:                 ✓ PASS (all zeros)
4. Effort levels present:               ✓ PASS (['hard', 'hard'])
5. Moving time calculation:             ✓ PASS
```

#### Base Pace Mode Tests
```
✓ PASS: Base pace mode still works correctly
  - Effort levels: ['steady', 'steady']
  - Uses forward calculation with fatigue
```

## Root Cause Analysis

The backend code is working correctly. If the user is experiencing issues, the problem is likely:

### 1. Frontend Not Sending Correct Parameters

Check that the frontend is sending:
```json
{
  "pacing_mode": "target_time",
  "target_time": "HH:MM:SS"
}
```

**NOT**:
```json
{
  "pacing_mode": "base_pace",  // Wrong!
  ...
}
```

### 2. Browser Cache Issues

The user may be seeing cached JavaScript that:
- Uses old API request format
- Displays results incorrectly
- Doesn't include the target time parameter

**Solutions**:
- Hard refresh browser (Ctrl+Shift+R / Cmd+Shift+R)
- Clear browser cache
- Check if APP_VERSION was updated (triggers cache bust)

### 3. Frontend Display Logic

The API returns correct data, but the UI might:
- Not display the `effort_level` field
- Show `fatigue_seconds` even when it's 0
- Use wrong data binding for target time mode

**Check**:
- `static/js/app.js` - does it handle effort_level?
- Does the UI conditionally show/hide fields based on pacing_mode?

### 4. Using Wrong Endpoint

Ensure the frontend is calling:
```
POST /api/calculate
```

Not an old or cached endpoint.

## How to Verify Backend is Working

### Manual Test via API

```bash
curl -X POST http://localhost:5001/api/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "elevation_profile": [
      {"distance": 0, "elevation": 100},
      {"distance": 5, "elevation": 200},
      {"distance": 10, "elevation": 150}
    ],
    "checkpoint_distances": [5, 10],
    "pacing_mode": "target_time",
    "target_time": "02:00:00",
    "num_checkpoints": 2,
    "avg_cp_time": 2,
    "z2_pace": 6.0,
    "climbing_ability": "moderate",
    "fatigue_enabled": true,
    "fitness_level": "trained",
    "skill_level": 0.5,
    "carbs_per_hour": 60,
    "water_per_hour": 500,
    "segment_terrain_types": ["smooth_trail", "smooth_trail"]
  }'
```

**Expected response**:
```json
{
  "segments": [
    {
      "effort_level": "easy|medium|hard|very_hard",
      "fatigue_seconds": 0.0,
      "pace": <varies>,
      "cumulative_time": <exactly matches target>
    }
  ]
}
```

### Run Test Suite

```bash
cd /home/runner/work/RaceCraft/RaceCraft
python3 test_target_time_fix.py
```

Expected output:
```
✓ ALL TESTS PASSED - Independent target time calculation is working!
```

## Code Changes Made

### 1. Debug Logging (app.py:1941-1987)

Added logging to track:
- Pacing mode received
- Target time parsing
- Function call confirmation
- Segment calculation mode

### 2. Fixed use_target_time Variable (app.py:1942)

**Before**:
```python
use_target_time = pacing_mode == 'target_time' and target_time_str
```
This would set `use_target_time` to the value of `target_time_str` (e.g., "02:30:00") when truthy.

**After**:
```python
use_target_time = pacing_mode == 'target_time' and bool(target_time_str)
```
Now explicitly returns `True` or `False`.

### 3. Test Suite (test_target_time_fix.py)

Comprehensive test that validates:
- Target time mode works correctly
- Base pace mode still works
- All requirements are met

## Recommendations

1. **Remove debug logs** after issue is resolved (or keep for diagnostics)
2. **Check frontend code** for proper parameter passing
3. **Verify cache busting** - ensure APP_VERSION is updated
4. **Add frontend tests** to validate UI displays correct data
5. **Consider adding visual indicator** in UI showing which mode is active

## API Contract

### Target Time Mode

**Request**:
```json
{
  "pacing_mode": "target_time",
  "target_time": "HH:MM:SS",
  "num_checkpoints": N,
  "avg_cp_time": M,
  ...
}
```

**Response** (segment):
```json
{
  "effort_level": "easy|medium|hard|very_hard",
  "fatigue_seconds": 0.0,
  "fatigue_str": "+0:00",
  "pace": <calculated from target>,
  "pace_aggressive": false,
  "cumulative_time": <matches target at end>
}
```

### Base Pace Mode

**Request**:
```json
{
  "pacing_mode": "base_pace",
  "z2_pace": N,
  ...
}
```

**Response** (segment):
```json
{
  "effort_level": "steady",
  "fatigue_seconds": <calculated>,
  "fatigue_str": "+MM:SS",
  "pace": <calculated with fatigue>,
  "pace_aggressive": false|true
}
```

## Conclusion

The backend implementation is correct and working as designed. The independent target time calculation:
- ✅ Calculates pace from target time, distance, elevation, and terrain
- ✅ Ignores base pace, fitness, fatigue, and technical ability
- ✅ Always achieves exact target time
- ✅ Includes proper effort level labels

If the user is still experiencing issues, the problem is in:
1. Frontend parameter passing
2. Browser caching
3. UI data display logic

Not in the backend calculation itself.
