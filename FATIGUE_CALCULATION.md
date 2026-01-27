# Fatigue Calculation Documentation

## Overview

The RaceCraft Fuel & Pacing Planner includes a sophisticated fatigue model that adjusts runner pace based on accumulated race time. This document explains how fatigue is calculated and applied to race segments.

## Key Concepts

Fatigue in endurance racing is the cumulative effect of time on feet that progressively slows down a runner's pace. The model assumes that the longer you've been running, the slower you will go, even on similar terrain.

## Configuration Parameters

### Fatigue Multipliers by Ability Level

The system uses ability-level-specific fatigue multipliers to account for different runner capabilities:

```python
ABILITY_FATIGUE_MAP = {
    'strong': 1.0,      # Experienced/elite runners
    'average': 2.0,     # Typical endurance runners
    'weak': 3.0         # Less experienced/struggling runners
}
```

- **Strong**: Minimal fatigue accumulation (1.0% per hour)
- **Average**: Moderate fatigue accumulation (2.0% per hour) - **Default**
- **Weak**: Significant fatigue accumulation (3.0% per hour)

### Other Constants

```python
FATIGUE_MULTIPLIER = 2.0           # Default multiplier (average ability)
MAX_DOWNHILL_SPEED_INCREASE = 20.0 # Maximum pace improvement on downhills (%)
```

## Calculation Process

The fatigue calculation is part of the `adjust_pace_for_elevation()` function and follows this sequence:

### Step 1: Calculate Base Pace with Elevation

First, the system calculates pace adjustments for elevation without fatigue:

```python
# Calculate elevation time impact
elev_time_seconds = (elevation_gain * elev_gain_factor) - (elevation_loss * elev_gain_factor * 0.3)
elev_time_minutes = elev_time_seconds / 60.0

# Calculate segment time and pace with elevation
segment_time_no_fatigue = (distance_km * base_pace) + elev_time_minutes
pace_with_elev_only = segment_time_no_fatigue / distance_km
```

**Notes:**
- Elevation gain adds time (6 seconds per meter by default)
- Elevation loss provides 30% benefit compared to gain
- Downhill speed increases are capped at 20% improvement

### Step 2: Apply Fatigue Factor

If fatigue is enabled, the system applies a progressive multiplier:

```python
if fatigue_enabled:
    fatigue_factor = 1.0 + (cumulative_time_hours * fatigue_multiplier / 100.0)
    fatigued_pace = pace_with_elev_limited * fatigue_factor
    fatigue_seconds_per_km = (fatigued_pace - pace_with_elev_limited) * 60.0
```

**Fatigue Factor Formula:**
```
fatigue_factor = 1.0 + (cumulative_time_hours × fatigue_multiplier / 100)
```

**Example Calculations:**

For an **average ability** runner (multiplier = 2.0):
- After 5 hours: `1.0 + (5 × 2.0 / 100) = 1.10` (10% slower)
- After 10 hours: `1.0 + (10 × 2.0 / 100) = 1.20` (20% slower)
- After 20 hours: `1.0 + (20 × 2.0 / 100) = 1.40` (40% slower)

For a **strong** runner (multiplier = 1.0):
- After 5 hours: `1.0 + (5 × 1.0 / 100) = 1.05` (5% slower)
- After 10 hours: `1.0 + (10 × 1.0 / 100) = 1.10` (10% slower)
- After 20 hours: `1.0 + (20 × 1.0 / 100) = 1.20` (20% slower)

For a **weak** runner (multiplier = 3.0):
- After 5 hours: `1.0 + (5 × 3.0 / 100) = 1.15` (15% slower)
- After 10 hours: `1.0 + (10 × 3.0 / 100) = 1.30` (30% slower)
- After 20 hours: `1.0 + (20 × 3.0 / 100) = 1.60` (60% slower)

### Step 3: Apply Terrain Difficulty (if enabled)

After fatigue, terrain difficulty adjustments are applied:

```python
difficulty_adjustment_seconds = DIFFICULTY_PACE_MAP.get(difficulty, 0)
difficulty_adjustment_minutes = difficulty_adjustment_seconds / 60.0
pace_with_difficulty = fatigued_pace + difficulty_adjustment_minutes
```

### Step 4: Cap Maximum Pace

Finally, the pace is capped to prevent unrealistic slowdowns:

```python
max_allowed_pace = base_pace * 2.0
final_pace = min(pace_with_difficulty, max_allowed_pace)
```

This ensures that pace never exceeds 2× the base Z2 pace, even with extreme fatigue.

## Cumulative Time Calculation

The `cumulative_time_hours` used in the fatigue formula represents **total moving time** (excluding checkpoint stops) accumulated up to the start of the current segment:

```python
cumulative_hours = total_moving_time / 60.0  # Convert minutes to hours
```

This means:
- First segment: No fatigue (0 hours accumulated)
- Each subsequent segment: Progressively more fatigue
- Fatigue compounds throughout the race

## Complete Example

**Scenario:** Average runner, 100km race, 15 hours moving time at segment 8

**Input Values:**
- Base pace: 7:00 min/km
- Cumulative time: 15 hours
- Fatigue multiplier: 2.0 (average)
- Segment: 5km with 200m gain, 50m loss

**Calculation:**

1. **Elevation adjustment:**
   - Gain time: 200m × 6s/m = 1,200s = 20 minutes
   - Loss benefit: 50m × 6s/m × 0.3 = 90s = 1.5 minutes
   - Net elevation time: 20 - 1.5 = 18.5 minutes
   - Pace with elevation: (5km × 7.0 + 18.5) / 5 = 10.7 min/km

2. **Fatigue application:**
   - Fatigue factor: 1.0 + (15 × 2.0 / 100) = 1.30
   - Fatigued pace: 10.7 × 1.30 = 13.91 min/km
   - Fatigue penalty: (13.91 - 10.7) × 60 = 193 seconds/km

3. **Result:**
   - Final pace: 13:55 min/km
   - Segment time: 69.5 minutes
   - Fatigue added: ~16 minutes to this segment

## Critical Understanding: Fatigue Compounds on Elevation-Adjusted Pace

**IMPORTANT:** Fatigue is applied as a percentage of your **elevation-adjusted pace**, not your base flat pace. This is a key feature of the model.

### Real-World Example

Consider a segment late in a 100km race:
- **Segment time:** 1:04:57
- **Cumulative time at segment start:** 13.47 hours
- **Base pace:** 7:00 min/km
- **Elevation adjustment:** Brings pace to 8:13 min/km
- **Ability level:** Average (2.0 multiplier)

**Calculation:**
1. Fatigue factor: `1.0 + (13.47 × 2.0 / 100) = 1.2693` (26.93% slower)
2. Fatigue is applied to **elevation-adjusted pace** of 8:13, not base pace of 7:00
3. Fatigue penalty: `26.93% of 8:13 = +2:13 per km`
4. Final pace: `8:13 × 1.2693 = 10:26 min/km`

### Why This Makes Sense

This compounding effect reflects real endurance racing physiology:

1. **Elevation already challenges you:** The climb slows you to 8:13 min/km
2. **Fatigue affects your actual effort:** After 13.5 hours, you're 26.93% slower at whatever you're doing
3. **Climbing when fatigued is harder:** The combination of elevation + fatigue compounds realistically
4. **Real-world validation:** Elite runners confirm that late-race climbs are disproportionately difficult

### Common Misconception

❌ **Incorrect:** "Fatigue should only apply to base pace"
- This would mean: 7:00 base → 8:53 with fatigue → ~9:00 final (only +7s for elevation effect)
- Unrealistic: Suggests elevation impact diminishes when fatigued

✅ **Correct:** "Fatigue applies to elevation-adjusted pace"
- This means: 7:00 base → 8:13 with elevation → 10:26 with fatigue
- Realistic: Climbing when exhausted is significantly harder

### Extreme Example (20+ hour race)

For a segment at 20 hours with average ability:
- Fatigue factor: `1.0 + (20 × 2.0 / 100) = 1.40` (40% slower)
- If elevation brings pace to 9:00 min/km
- Fatigue penalty: `40% of 9:00 = +3:36 per km`
- Final pace: 12:36 min/km

This may seem extreme, but it accurately models the reality that:
- At 20+ hours, everything is harder
- Climbs that would normally add 2 min/km might add 3-4 min/km when exhausted
- The model caps at 2× base pace to prevent unrealistic extremes

## User Interface

In the application:
- **Checkbox:** "Include Fatigue Penalty" (enabled by default)
- **Ability Level Dropdown:** Strong, Average, Weak
- **Results Table:** Shows fatigue penalty as "+MM:SS" per kilometer
- **Cumulative Effect:** Each segment's fatigue compounds on previous segments

## Disabling Fatigue

When fatigue is disabled:
```python
fatigue_enabled = False
fatigued_pace = pace_with_elev_limited  # No fatigue factor applied
fatigue_seconds_per_km = 0.0
```

The pace calculation uses only elevation and terrain difficulty adjustments.

## Design Rationale

### Why Linear Accumulation?

The linear fatigue model (`fatigue_factor = 1.0 + (hours × multiplier / 100)`) provides:
- Predictable, understandable results
- Progressive slowdown that matches real-world endurance racing experiences
- Easy calibration through ability levels

### Why Different Ability Levels?

Runner experience significantly affects fatigue resistance:
- **Elite/experienced runners:** Better pacing, nutrition, and mental toughness
- **Average runners:** Standard endurance racing fatigue patterns
- **Less experienced:** May struggle with pacing, nutrition, or physical conditioning

### Limitations

This model:
- Assumes consistent fatigue accumulation (doesn't account for "second winds")
- Doesn't model recovery at aid stations
- Doesn't account for time-of-day effects (night running, circadian rhythms)
- Uses a simplified linear model (real fatigue may be exponential in some cases)

## Best Practices

1. **Choose appropriate ability level:**
   - Strong: 10+ long-distance races, consistent pacing experience
   - Average: 3-10 long-distance races, typical runner
   - Weak: First long-distance race or known pacing struggles

2. **Consider the race distance:**
   - Shorter (50km): Fatigue less significant
   - Medium (100km): Fatigue becomes major factor
   - Long (100+ miles): Fatigue dominates later stages

3. **Compare with/without fatigue:**
   - Calculate both scenarios to understand impact
   - Use conservative (average/weak) settings for planning

4. **Validate with training data:**
   - Compare predicted vs. actual fatigue in training runs
   - Adjust ability level based on historical performance

## Related Features

- **Elevation Adjustment:** Applied before fatigue
- **Terrain Difficulty:** Applied after fatigue
- **Checkpoint Stops:** Not included in cumulative time (fatigue based on moving time only)
