# Climbing Model Refactoring - Change Summary

## Overview
Successfully replaced the penalty-based elevation gain system with an intuitive, effort-based climbing model using vertical speed (m/h). The new model provides gradient-aware climbing efficiency, separate downhill handling, and human-readable climbing ability controls.

## Files Modified

### 1. Backend: [app.py](app.py)

#### Constants Added
- **CLIMBING_ABILITY_PARAMS**: Maps climbing abilities to vertical speeds
  - Conservative: 500 m/h
  - Moderate: 700 m/h
  - Strong: 900 m/h
  - Very Strong: 1100 m/h
  - Elite: 1300 m/h

- **DOWNHILL_SPEED_MULTIPLIERS**: Gradient-based downhill speed multipliers
  - 0-5%: 1.05×
  - 5-10%: 1.15×
  - 10-15%: 1.20× (peak)
  - >15%: 1.10× (forced slowdown)

#### Constants Removed
- `ELEVATION_GAIN_FACTOR` (was 6.0 sec/m)
- `MAX_DOWNHILL_SPEED_INCREASE` (was 20%)

#### New Functions

**calculate_vertical_speed(base_vertical_speed, gradient)**
- Implements gradient-aware efficiency curve
- <5%: 60% efficiency (gentle, minimal climb cost)
- 8-12%: 100% efficiency (peak climbing zone)
- >15%: Declining to 65% (forced hiking)

**calculate_downhill_multiplier(gradient, terrain_type)**
- Calculates terrain-aware downhill speed multipliers
- Caps maximum speed based on terrain difficulty
- Technical terrain = slower safe descent speed

#### Refactored Functions

**adjust_pace_for_elevation(...)**
- Changed signature: `elev_gain_factor` → `climbing_ability`
- Implements additive model: `segment_time = horizontal_time + climb_time - descent_savings`
- Horizontal time: `distance / base_pace_kmh`
- Climb time: `ascent / vertical_speed`
- Descent savings: Based on downhill multiplier
- Applies terrain and fatigue multipliers to total time

**calculate() API endpoint**
- Changed input parameter: `elev_gain_factor` → `climbing_ability`
- Passes string ability level instead of numeric factor

**save_plan() and load_plan()**
- Updated to save/load `climbing_ability` instead of `elev_gain_factor`

### 2. Frontend: [templates/index.html](templates/index.html)

#### UI Changes
Replaced elevation gain factor control:
```html
<!-- OLD -->
<input type="number" id="elev-gain-factor" min="0" step="0.1" value="6.0" />

<!-- NEW -->
<select id="climbing-ability">
    <option value="conservative">Conservative Climber (500 m/h)</option>
    <option value="moderate" selected>Moderate Climber (700 m/h)</option>
    <option value="strong">Strong Climber (900 m/h)</option>
    <option value="very_strong">Very Strong Climber (1100 m/h)</option>
    <option value="elite">Elite Climber (1300 m/h)</option>
</select>
```

### 3. Frontend: [static/js/app.js](static/js/app.js)

#### Changes Made
- **calculateRacePlan()**: Get `climbing-ability` value instead of `elev-gain-factor`
- **Request data**: Send `climbing_ability` string to backend
- **savePlan()**: Save `climbing_ability` instead of `elev_gain_factor`
- **loadPlan()**: Load `climbing_ability` with fallback to 'moderate'
- **clearAll()**: Reset to 'moderate' instead of 6.0

## New Documentation

### [CLIMBING_MODEL.md](CLIMBING_MODEL.md)
Comprehensive documentation covering:
- Additive time model formula and rationale
- Vertical speed ranges and calibration guidelines
- Gradient-aware efficiency curve explanation
- Downhill speed model with terrain capping
- Integration with fatigue and terrain systems
- Comparison with old penalty-based model
- User interface guidelines
- Example calculations

### [test_climbing_model.py](test_climbing_model.py)
Verification script demonstrating:
- Gradient-aware vertical speed calculations
- Climbing time for different ability levels
- Downhill speed multipliers by terrain
- Complete segment calculation with all factors

## Key Model Improvements

### 1. Additive vs Penalty Model

**Old Approach:**
```python
segment_time = distance × pace + elevation_gain × factor
```
- Abstract factor (6 sec/m)
- No gradient awareness
- Downhill as negative penalty

**New Approach:**
```python
segment_time = horizontal_time + climb_time - descent_savings
horizontal_time = distance / base_pace_kmh
climb_time = ascent / vertical_speed
```
- Intuitive vertical speed (m/h)
- Gradient-aware efficiency
- Separate downhill model

### 2. Gradient Awareness

Climbing efficiency now varies realistically:
- **<5% grade**: 60% efficient (not in "climbing mode")
- **8-12% grade**: 100% efficient (optimal biomechanics)
- **>15% grade**: Declining efficiency (forced hiking)

### 3. Downhill Realism

Downhills now have:
- Gradient-based speed multipliers (faster on moderate slopes)
- Terrain-based caps (technical terrain limits safe speed)
- Peak efficiency at 10-15% grade
- Forced slowdown on very steep descents

### 4. User Experience

Users now:
- Select human-readable climbing ability
- Understand vertical speed (800 m/h) better than abstract factors
- Can calibrate based on known climb performances
- Get more realistic predictions

## Integration with Existing Systems

The new model works seamlessly with:

✅ **Fatigue System**: Cumulative km-effort tracked, multiplier applied after base time  
✅ **Terrain Difficulty**: Local efficiency factor applied to segment time  
✅ **Technical Skill**: Still modulates terrain impact  
✅ **Checkpoint Planning**: No changes needed  
✅ **Nutrition Calculations**: Based on segment time (unchanged interface)  

## Backward Compatibility

⚠️ **Saved Plans**: Old plans with `elev_gain_factor` will default to 'moderate' climbing ability

Migration strategy:
- Load existing plans → Default to 'moderate' (700 m/h)
- Users can adjust climbing ability and re-save
- No data loss, just need to re-calibrate climbing setting

## Testing Results

Verified functionality:
- ✅ Gradient efficiency curve working correctly
- ✅ Downhill multipliers terrain-aware
- ✅ Additive model produces realistic times
- ✅ Integration with fatigue/terrain multipliers
- ✅ All ability levels produce reasonable outputs

Example validation (3 km, +300m, moderate climber):
- Horizontal: 19.5 min
- Climbing: 25.7 min
- Base time: 45.2 min
- With terrain (1.33×): 60.1 min
- With fatigue (1.15×): 69.2 min
- **Final pace: 23:03 min/km** ✅ Realistic for technical climbing segment

## Summary of Benefits

1. **More Intuitive**: "I climb at 800 m/h" vs "6 seconds per meter elevation gain"
2. **More Accurate**: Gradient-aware efficiency reflects real biomechanics
3. **Better Downhills**: Separate model with terrain-based speed caps
4. **Cleaner Code**: Separate concerns (horizontal, vertical, descent)
5. **Better UX**: Simple dropdown instead of numeric slider
6. **Calibration**: Athletes can measure vertical speed on known climbs
7. **Future-Proof**: Easy to add altitude, temperature, surface type effects

## Next Steps (Optional Enhancements)

Consider future additions:
- [ ] Custom vertical speed input option
- [ ] Altitude adjustment (reduced efficiency at elevation)
- [ ] Climb length factor (efficiency changes on long climbs)
- [ ] Temperature impact on climbing performance
- [ ] Surface-specific vertical speeds (trail vs road vs stairs)
