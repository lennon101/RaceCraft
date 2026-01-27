# Fatigue Model Documentation

## Overview

RaceCraft uses an **effort-based, fitness-dependent fatigue model** that more accurately reflects how fatigue affects endurance athletes during long races. Unlike simple time-based models, this approach accounts for cumulative effort (including vertical gain), delays fatigue onset based on fitness level, and applies non-linear compounding after a threshold is exceeded.

## Core Principles

1. **Effort-Based**: Fatigue is driven by cumulative effort, not just distance or time
2. **Delayed Onset**: No fatigue penalty until a fitness-dependent threshold is exceeded
3. **Non-Linear**: Fatigue compounds progressively as effort increases beyond the threshold
4. **Fitness-Dependent**: Fitter athletes have higher thresholds and slower fatigue accumulation

## Cumulative Effort Calculation

Effort is measured in **km-effort**, which accounts for both horizontal distance and vertical movement:

```
effort_km = distance_km + (ascent_m / 100) + (descent_m / 200)
```

### Why This Formula?

- **Distance**: Base effort from forward movement
- **Ascent penalty**: Every 100m of climbing = 1 km of horizontal effort (based on Naismith's Rule)
- **Descent penalty**: Every 200m of descent = 1 km of horizontal effort (descending costs ~50% of climbing due to eccentric muscle loading and impact forces)

### Example

A 10 km segment with 500m ascent and 300m descent:
```
effort_km = 10 + (500/100) + (300/200)
effort_km = 10 + 5 + 1.5 = 16.5 km-effort
```

## Fatigue Onset Point (FOP)

Each athlete has a **Fatigue Onset Point** representing how much cumulative effort they can sustain before fatigue begins affecting performance. FOP values are in km-effort:

| Fitness Level | FOP Range | α (Severity) | β (Compounding) |
|--------------|-----------|--------------|-----------------|
| **Untrained** | 20-30 km | 0.35 | 1.8 |
| **Recreational** | 30-45 km | 0.25 | 1.5 |
| **Trained** | 45-65 km | 0.20 | 1.4 |
| **Elite** | 65-85+ km | 0.15 | 1.3 |

### Fitness Level Definitions

- **Untrained**: New to endurance racing, limited endurance base
- **Recreational**: Regular runner, some long-distance experience, moderate endurance
- **Trained**: Consistent training, multiple long-distance races completed, strong endurance base
- **Elite**: High-volume training, competitive endurance athlete, exceptional durability

## Fatigue Multiplier Formula

The fatigue multiplier applies to all pace components (flat, climb, descent) after FOP is exceeded:

```
fatigue_multiplier = 1 + α × ((E − FOP) / FOP)^β
```

Where:
- **E** = cumulative effort (km-effort)
- **FOP** = Fatigue Onset Point (km-effort)
- **α** = Severity coefficient (controls maximum fatigue)
- **β** = Compounding exponent (controls how sharply fatigue increases)

### How It Works

1. **Before FOP**: `fatigue_multiplier = 1.0` (no slowdown)
2. **At FOP**: `fatigue_multiplier = 1.0` (fatigue just beginning)
3. **After FOP**: Multiplier increases non-linearly based on how far beyond FOP

### Example Calculations

**Recreational runner (FOP = 37.5 km, α = 0.25, β = 1.5):**

At 50 km cumulative effort:
```
fatigue_multiplier = 1 + 0.25 × ((50 - 37.5) / 37.5)^1.5
fatigue_multiplier = 1 + 0.25 × (0.333)^1.5
fatigue_multiplier = 1 + 0.25 × 0.192
fatigue_multiplier = 1.048 (4.8% slower)
```

At 75 km cumulative effort:
```
fatigue_multiplier = 1 + 0.25 × ((75 - 37.5) / 37.5)^1.5
fatigue_multiplier = 1 + 0.25 × (1.0)^1.5
fatigue_multiplier = 1.25 (25% slower)
```

At 100 km cumulative effort:
```
fatigue_multiplier = 1 + 0.25 × ((100 - 37.5) / 37.5)^1.5
fatigue_multiplier = 1 + 0.25 × (1.667)^1.5
fatigue_multiplier = 1.539 (53.9% slower)
```

## Pace Calculation Pipeline

The complete pace adjustment happens in this order:

### 1. Base Pace
Your Zone 2 flat-ground pace (e.g., 6:30 min/km)

### 2. Elevation Adjustment
```
elev_time_seconds = (ascent_m × gain_factor) - (descent_m × gain_factor × 0.3)
pace_with_elev = (distance_km × base_pace + elev_time_minutes) / distance_km
```
- Default gain factor: 6 seconds per meter of ascent
- Descents provide a 30% time credit

### 3. Fatigue Adjustment (NEW)
```
IF cumulative_effort > FOP:
    fatigue_multiplier = 1 + α × ((E − FOP) / FOP)^β
    fatigued_pace = pace_with_elev × fatigue_multiplier
ELSE:
    fatigued_pace = pace_with_elev
```

### 4. Terrain Difficulty Adjustment
Additional time penalties/credits for technical terrain:
- **Easy/Road**: -10 sec/km
- **Normal**: 0 sec/km
- **Technical Uphill**: +10 sec/km
- **Technical Downhill**: +20 sec/km

### 5. Safety Caps
- **Minimum pace**: 80% of base pace (limits downhill speed boost)
- **Maximum pace**: 200% of base pace (prevents unrealistic slowdowns)

## Comparison: Old vs New Model

### Old Model (Time-Based)
```
fatigue_factor = 1 + (cumulative_hours × ability_multiplier / 100)
- Strong: 1% per hour
- Average: 2% per hour  
- Weak: 3% per hour
```

**Problems:**
- Fatigue starts immediately from the beginning
- Linear accumulation doesn't reflect reality
- Ignores vertical gain in fatigue calculation
- Same rate for flat vs mountainous courses

### New Model (Effort-Based)
```
effort_km = distance + ascent/100 + descent/200
IF effort > FOP:
    fatigue_multiplier = 1 + α × ((effort − FOP) / FOP)^β
```

**Advantages:**
- No fatigue until fitness threshold exceeded
- Non-linear compounding reflects progressive breakdown
- Vertical gain drives fatigue accumulation
- Fitter athletes have higher thresholds and slower accumulation
- More accurate for mountainous races

## Practical Examples

### Example 1: 50km Mountain Race (Recreational Runner)

**Route:** 50km, 3000m ascent, 3000m descent
```
Cumulative effort = 50 + (3000/100) + (3000/200)
                  = 50 + 30 + 15 = 95 km-effort
```

**Fatigue progression (FOP = 37.5 km):**
- 0-37.5 km-effort: No fatigue penalty (fresh)
- 40 km-effort: 1.015× (1.5% slower)
- 50 km-effort: 1.048× (4.8% slower)
- 70 km-effort: 1.186× (18.6% slower)
- 95 km-effort: 1.565× (56.5% slower)

### Example 2: 100km Relatively Flat (Elite Runner)

**Route:** 100km, 1000m ascent, 1000m descent
```
Cumulative effort = 100 + (1000/100) + (1000/200)
                  = 100 + 10 + 5 = 115 km-effort
```

**Fatigue progression (FOP = 75 km):**
- 0-75 km-effort: No fatigue penalty
- 80 km-effort: 1.010× (1.0% slower)
- 90 km-effort: 1.036× (3.6% slower)
- 100 km-effort: 1.071× (7.1% slower)
- 115 km-effort: 1.130× (13.0% slower)

The elite runner maintains pace much longer and accumulates fatigue more slowly.

## Advanced Considerations

### Heat & Environmental Factors
In extreme heat or adverse conditions, consider:
- Reducing FOP by 10-20%
- Increasing α by 0.05-0.10

Example: Recreational runner in extreme heat
- Normal: FOP = 37.5, α = 0.25
- Adjusted: FOP = 32, α = 0.30

### Fuelling & Hydration
Poor fuelling can accelerate fatigue:
- Under-fuelling: Reduce FOP by 15%, increase α by 0.08
- Proper fuelling: Use standard values
- Optimal fuelling: Can increase FOP by 5-10%

### Late-Race Descent Penalty
The model already accounts for descents in effort calculation (1 km per 200m descent), which reflects the eccentric muscle damage that accumulates throughout the race. This penalty is applied continuously as cumulative effort increases.

## Tuning Recommendations

### For Race Directors / Course Designers
1. Calculate total course effort to understand difficulty
2. Courses with >1.5:1 effort-to-distance ratio are significantly harder
3. Example: 100km with 5000m vert = 175 km-effort (1.75 ratio)

### For Athletes
1. **Testing**: Use training runs to calibrate your FOP
2. **Conservative start**: Stay well below FOP early in race
3. **Monitor effort**: Track cumulative effort, not just distance
4. **Pacing strategy**: Bank time early (before FOP) when running efficiently

### Model Calibration
To calibrate your personal FOP:
1. Find a training run where you maintained even effort to failure
2. Calculate cumulative effort where pace significantly slowed
3. That's approximately your FOP

## Technical Implementation

See [app.py](app.py) for the complete implementation:

```python
# Fitness parameters
FITNESS_LEVEL_PARAMS = {
    'untrained': {'fop': 25, 'alpha': 0.35, 'beta': 1.8},
    'recreational': {'fop': 37.5, 'alpha': 0.25, 'beta': 1.5},
    'trained': {'fop': 55, 'alpha': 0.20, 'beta': 1.4},
    'elite': {'fop': 75, 'alpha': 0.15, 'beta': 1.3}
}

# Effort calculation (per segment)
segment_effort = distance_km + (ascent_m / 100.0) + (descent_m / 200.0)

# Fatigue multiplier (if cumulative_effort > FOP)
fatigue_multiplier = 1.0 + alpha * (((cumulative_effort - fop) / fop) ** beta)
```

## References

This model is inspired by research in endurance running physiology and builds upon concepts from:
- Naismith's Rule (1892) for climbing time estimation
- ITRA Performance Index for vertical gain equivalents
- Observational data from endurance race splits
- Physiological studies on non-linear fatigue accumulation

## Future Enhancements

Potential model improvements:
1. **Heat adjustment**: Automatic FOP reduction based on temperature data
2. **Time-of-day**: Circadian rhythm effects on late-night/early-morning segments
3. **Surface type**: Different descent penalties for technical vs runnable terrain
4. **Individual calibration**: Learn personal α, β, FOP from historical race data
5. **Recovery segments**: Slight FOP recovery during aid station breaks

---

*For questions or feedback about the fatigue model, please open an issue on the project repository.*
