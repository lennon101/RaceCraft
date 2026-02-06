# Climbing Model Documentation

## Overview

RaceCraft uses an **intuitive, effort-based climbing model** that separates horizontal movement from vertical climbing using **vertical speed** (m/h) instead of penalty-based elevation factors. This approach more accurately reflects how athletes experience climbing in mountain races.

## Core Principles

1. **Additive Model**: Segment time combines horizontal movement, climbing time, and descent adjustments separately
2. **Vertical Speed**: Climbing ability expressed as sustainable vertical speed (m/h) rather than time penalties
3. **Gradient-Aware**: Vertical speed efficiency varies with gradient (optimal at 8-12%, declining above 15%)
4. **Separate Downhills**: Downhill speed modeled with capped multipliers based on gradient and terrain
5. **Clean Integration**: Works seamlessly with existing fatigue and terrain-difficulty multipliers

## Additive Time Model

### Formula

```
segment_time = horizontal_time + climb_time - descent_time_savings
```

Where:

- **horizontal_time** = distance_km / base_pace_kmh × 60 (minutes)
- **climb_time** = ascent_m / vertical_speed × 60 (minutes)
- **descent_time_savings** = time saved on downhills based on gradient

### Why Additive?

Traditional penalty-based models (`distance × pace + elevation_gain × factor`) treat climbing as an abstract cost added to flat pace. The additive model better reflects reality:

- **Horizontal**: Time to cover ground distance at flat pace
- **Climbing**: Additional time required to gain elevation
- **Descent**: Time saved (or lost) going downhill

This separation makes the model more intuitive and allows gradient-aware adjustments.

## Vertical Speed

### Climbing Ability Levels

Athletes have a sustainable **vertical speed** representing their climbing ability:

| Ability Level | Vertical Speed | Description |
|--------------|----------------|-------------|
| **Conservative** | 500 m/h | Untrained or conservative climbing approach |
| **Moderate** | 700 m/h | Recreational runner, average climbing fitness |
| **Strong** | 900 m/h | Trained climber, good mountain running ability |
| **Very Strong** | 1100 m/h | Experienced mountain athlete |
| **Elite** | 1300 m/h | Elite mountain runner |

### Reference Points

- **Untrained**: 400-600 m/h
- **Recreational**: 600-800 m/h
- **Trained**: 800-1000 m/h
- **Elite**: 1000-1400+ m/h

### Example Calculation

**Scenario**: 5 km segment with 500m climb, moderate climber (700 m/h), 6:30 flat pace

```
base_pace = 60 / 6.5 = 9.23 km/h
horizontal_time = 5 / 9.23 × 60 = 32.5 minutes
climb_time = 500 / 700 × 60 = 42.9 minutes
segment_time = 32.5 + 42.9 = 75.4 minutes
pace = 75.4 / 5 = 15:05 min/km
```

## Gradient-Aware Efficiency

Vertical speed is **not constant** across all gradients. Biomechanical efficiency varies:

### Efficiency Curve

| Gradient Range | Efficiency | Reasoning |
|---------------|-----------|-----------|
| **<5%** | 60% | Very gentle, minimal climb cost, not in "climbing mode" |
| **5-8%** | 60-100% | Transitioning to optimal climbing gait |
| **8-12%** | 100% | **Peak efficiency** - optimal sustainable climbing grade |
| **12-15%** | 100-85% | Getting steep, efficiency declining |
| **15-20%** | 85-65% | Forced hiking, biomechanical limits |
| **>20%** | 65% | Very steep, significantly slower |

### Implementation

```python
def calculate_vertical_speed(base_vertical_speed, gradient):
    gradient_pct = abs(gradient) * 100.0
    
    if gradient_pct < 5.0:
        efficiency = 0.60
    elif gradient_pct < 8.0:
        efficiency = 0.60 + (gradient_pct - 5.0) / 3.0 * 0.40
    elif gradient_pct <= 12.0:
        efficiency = 1.0  # Peak efficiency
    elif gradient_pct <= 15.0:
        efficiency = 1.0 - (gradient_pct - 12.0) / 3.0 * 0.15
    elif gradient_pct <= 20.0:
        efficiency = 0.85 - (gradient_pct - 15.0) / 5.0 * 0.20
    else:
        efficiency = 0.65
    
    return base_vertical_speed * efficiency
```

### Why This Matters

- **Gentle grades (<5%)**: Walking or running with minimal "climbing feel" - reduced efficiency
- **Moderate grades (8-12%)**: Optimal biomechanical position for power hiking or climbing
- **Steep grades (>15%)**: Forced to slow down, loss of rhythm, increased energy cost per meter

## Downhill Speed Model

Downhills are modeled **separately** using speed multipliers rather than negative climb penalties.

### Downhill Speed Multipliers

| Gradient Range | Base Multiplier | Effect |
|---------------|-----------------|---------|
| **0-5%** | 1.05× | Slight speedup |
| **5-10%** | 1.15× | Moderate speedup |
| **10-15%** | 1.20× | Maximum efficient speedup |
| **>15%** | 1.10× | Forced to slow down (steep, technical) |

### Terrain Capping

Downhill speed is **capped by terrain** for safety and control:

| Terrain Type | Terrain Cap | Effective Max Multiplier |
|-------------|-------------|-------------------------|
| Road | 100% | 1.20× |
| Smooth Trail | 95% | 1.19× |
| Dirt Road | 90% | 1.18× |
| Rocky Runnable | 80% | 1.16× |
| Technical | 70% | 1.14× |
| Very Technical | 60% | 1.12× |
| Scrambling | 50% | 1.10× |

### Implementation

```python
def calculate_downhill_multiplier(gradient, terrain_type='smooth_trail'):
    if gradient >= 0:
        return 1.0  # Not a downhill
    
    gradient_pct = abs(gradient) * 100.0
    
    # Base multiplier by gradient
    if gradient_pct <= 5.0:
        base_multiplier = 1.05
    elif gradient_pct <= 10.0:
        base_multiplier = 1.15
    elif gradient_pct <= 15.0:
        base_multiplier = 1.20
    else:
        base_multiplier = 1.10
    
    # Apply terrain cap
    terrain_cap = terrain_downhill_caps.get(terrain_type, 0.90)
    adjusted_multiplier = 1.0 + (base_multiplier - 1.0) * terrain_cap
    
    return adjusted_multiplier
```

### Why Separate Downhill Model?

- **Asymmetric**: Downhills don't mirror uphills - different biomechanics
- **Terrain-Dependent**: Technical terrain limits safe downhill speed more than uphills
- **Realistic**: Athletes know they can't bomb down technical descents at 1.5× pace

## Integration with Fatigue and Terrain

The climbing model works **cleanly** with existing systems:

### Application Order

1. **Base Time**: Calculate using additive model (horizontal + climb - descent)
2. **Terrain Factor**: Apply local efficiency penalty for terrain difficulty
3. **Fatigue Multiplier**: Apply cumulative fatigue based on effort

```python
base_segment_time = horizontal_time + climb_time - descent_savings
adjusted_time = base_segment_time × terrain_factor × fatigue_multiplier
```

### Key Properties

- **Fatigue** is cumulative and global (tracks total effort)
- **Terrain** affects local efficiency only (doesn't accumulate)
- **Climbing** is part of base time calculation
- **All three** multiply together cleanly

### Example

**Segment**: 3 km, 300m climb, 50m descent
**Athlete**: Moderate climber (700 m/h), 6:30 flat pace
**Terrain**: Technical trail (1.33× factor)
**Fatigue**: 1.15× multiplier (late in race)

```
horizontal_time = 3 / 9.23 × 60 = 19.5 min
climb_time = 300 / 700 × 60 = 25.7 min
base_time = 19.5 + 25.7 = 45.2 min

terrain_adjusted = 45.2 × 1.33 = 60.1 min
fatigue_adjusted = 60.1 × 1.15 = 69.1 min

final_pace = 69.1 / 3 = 23:02 min/km
```

## Advantages Over Penalty Model

### Old Model (Penalty-Based)

```
segment_time = distance × pace + elevation_gain × factor - elevation_loss × factor × 0.3
```

**Problems**:
- Factor (e.g., 6 sec/m) is abstract and hard to understand
- Same factor applied regardless of gradient
- Downhill as "negative penalty" doesn't reflect reality
- No intuitive mapping to athlete ability

### New Model (Vertical Speed)

```
segment_time = distance / speed + ascent / vertical_speed + downhill_adjustment
```

**Advantages**:
- **Intuitive**: "I climb at 800 m/h" is meaningful to athletes
- **Gradient-Aware**: Efficiency varies realistically with steepness
- **Separate Downhills**: Modeled independently with terrain-aware caps
- **Physically Grounded**: Based on actual climbing speeds, not abstract penalties

## User Interface

Athletes select climbing ability from a **simple dropdown**:

```html
<select id="climbing-ability">
    <option value="conservative">Conservative Climber (500 m/h)</option>
    <option value="moderate" selected>Moderate Climber (700 m/h)</option>
    <option value="strong">Strong Climber (900 m/h)</option>
    <option value="very_strong">Very Strong Climber (1100 m/h)</option>
    <option value="elite">Elite Climber (1300 m/h)</option>
</select>
```

**No more**:
- Abstract "elevation gain factor" sliders
- Confusion about seconds per meter
- Trial and error to find reasonable values

## Calibration Guidelines

To help athletes choose their climbing ability:

### Method 1: Known Climb Performance

If you know your time on a specific climb:
```
vertical_speed = elevation_gain_m / (time_minutes / 60)
```

Example: 500m climb in 45 minutes → 667 m/h → **Moderate Climber**

### Method 2: Reference Races

- **Conservative (500 m/h)**: New to mountain running, hiking most climbs
- **Moderate (700 m/h)**: Regular trail runner, can run/hike moderate grades
- **Strong (900 m/h)**: Experienced mountain runner, strong on climbs
- **Very Strong (1100 m/h)**: Competitive mountain runner
- **Elite (1300 m/h)**: Elite skyrunner/mountain athlete

### Method 3: Comparative Performance

Compare your climbing to flat running:
- **Conservative**: Climbs feel significantly harder than flats
- **Moderate**: Comfortable power hiking, can maintain rhythm
- **Strong**: Confident on climbs, often pass others
- **Very Strong**: Climbs are a strength, gain time on ascents
- **Elite**: Exceptional climbing ability, minimal time loss

## Technical Implementation Notes

### Code Structure

1. **Constants** (`app.py`):
   - `CLIMBING_ABILITY_PARAMS`: Maps ability levels to vertical speeds
   - `DOWNHILL_SPEED_MULTIPLIERS`: Gradient-based multipliers

2. **Functions** (`app.py`):
   - `calculate_vertical_speed()`: Gradient-aware efficiency adjustment
   - `calculate_downhill_multiplier()`: Terrain-aware downhill speed
   - `adjust_pace_for_elevation()`: Main additive model implementation

3. **Frontend** (`index.html` + `app.js`):
   - Climbing ability dropdown replaces elevation gain factor slider
   - Backend receives `climbing_ability` string instead of numeric factor

### Backward Compatibility

Old saved plans with `elev_gain_factor` will need migration or default to `'moderate'` climbing ability.

## Future Enhancements

Potential improvements:

1. **Custom Vertical Speed**: Allow users to input exact vertical speed value
2. **Altitude Adjustment**: Reduce vertical speed at higher elevations
3. **Climb Length Factor**: Efficiency changes on very long vs short climbs
4. **Temperature Impact**: Heat/cold affecting climbing performance
5. **Surface Type**: Different vertical speeds for trail vs road climbs

## Summary

The new climbing model provides:

✅ **Intuitive Control**: Human-readable climbing ability selection  
✅ **Gradient Awareness**: Efficiency varies realistically with steepness  
✅ **Separate Downhills**: Terrain-aware speed multipliers  
✅ **Clean Integration**: Works seamlessly with fatigue and terrain systems  
✅ **Physically Grounded**: Based on actual vertical speeds, not abstract factors  

Athletes can now understand and calibrate their race plans using familiar concepts like "I climb at 800 m/h" rather than abstract penalty factors.
