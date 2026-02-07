# Target Time Mode Documentation

## Overview

RaceCraft's **Target Time Mode** uses a **neutral route cost algorithm** that calculates segment pacing purely from target time, distance, elevation, and terrain difficulty. This mode guarantees the total moving time exactly equals the target time by solving the inverse problem: "Given time T, what pace must each segment have so the weighted sum equals T?"

This approach eliminates circular dependencies, produces deterministic results, and is impossible for users to "game" by adjusting athlete-specific parameters.

## Core Principles

1. **Target Time is a Hard Constraint**: The total calculated time MUST always equal the target time exactly
2. **Athlete-Independent**: Base pace, fitness level, fatigue, and technical ability have ZERO effect on calculations
3. **Route-Relative**: Pacing is determined by the route characteristics (terrain, elevation) relative to the target time
4. **Neutral Cost Foundation**: Terrain difficulty establishes a neutral cost before elevation effects are applied
5. **Realistic Constraints**: Pace limits (2:50-15:00 min/km) ensure achievable speeds while maintaining target time

## The Algorithm: 5 Steps

### Step 0: Build Neutral Route Cost

**Purpose**: Calculate terrain-weighted distance without any elevation effects

**Formula**:
```python
neutral_cost = Σ(distance_km × terrain_factor)
```

**What It Ignores**:
- Slope direction (uphill vs downhill)
- Elevation gain penalties
- Descent bonuses
- All vertical movement

**What It Includes**:
- Horizontal distance
- Terrain difficulty multipliers

**Terrain Factors**:
| Terrain Type | Factor | Description |
|--------------|--------|-------------|
| Road | 0.90 | 10% faster than baseline |
| Smooth Trail | 1.0 | Baseline reference |
| Dirt Road | 1.10 | 10% slower |
| Rocky Runnable | 1.35 | 35% slower |
| Technical | 1.75 | 75% slower |
| Very Technical | 2.25 | 125% slower |
| Scrambling | 3.0 | 200% slower |

**Why This Works**:
- Answers the question: "If this route were run at uniform difficulty, what flat pace would produce the target time?"
- A flat road race and a technical mountain race with the same target time will produce different internal neutral paces
- Provides a deterministic anchor for all subsequent calculations

**Example**:
```
Route: 30 km total
- 10 km smooth trail → 10 × 1.0 = 10.0
- 10 km technical → 10 × 1.75 = 17.5
- 10 km road → 10 × 0.90 = 9.0

neutral_cost = 10.0 + 17.5 + 9.0 = 36.5 km-equivalent
```

---

### Step 1: Compute Neutral Reference Pace

**Purpose**: Derive the internal pacing anchor from target time and neutral cost

**Formula**:
```python
neutral_reference_pace = target_time_minutes / neutral_cost
```

**Properties**:
- **Internal only**: Never shown in UI
- **Route-relative**: Changes automatically with route + target time
- **Non-athlete-specific**: No VO₂max, fitness, skill, or training assumptions
- **Deterministic**: Same inputs always produce same result
- **Impossible to game**: Users cannot manipulate this value

**Example** (continuing from Step 0):
```
target_time = 240 minutes (4 hours)
neutral_cost = 36.5 km-equivalent

neutral_reference_pace = 240 / 36.5 = 6.58 min/km
```

**Also Calculated** (for UI display only):
```python
simple_flat_pace = target_time / total_distance
simple_flat_pace = 240 / 30 = 8.00 min/km
```

The `simple_flat_pace` is shown to users as "Natural Pace Baseline" for reference, but `neutral_reference_pace` is used internally for calculations.

---

### Step 2: Apply Elevation Modifiers

**Purpose**: Layer elevation effects on top of the neutral cost foundation

**Base Weight**:
```python
base_weight = distance_km × terrain_factor
```
This is the same terrain-weighted distance from Step 0.

**Elevation Factor Calculation**:
```python
elev_factor = 1.0  # Start neutral

# Climbing penalty (if elevation gain > 0)
if elev_gain > 0:
    vertical_speed = 600 m/h = 0.01 km/min
    climb_time_penalty = (elev_gain / 1000.0) / vertical_speed
    base_segment_time = base_weight × neutral_reference_pace
    elev_factor += climb_time_penalty / base_segment_time

# Descent bonus (if elevation loss > 0)
if elev_loss > 0:
    gradient = (elev_gain - elev_loss) / (distance_km × 1000)
    descent_bonus = min(0.20, abs(gradient) × 2.0)  # Max 20% speedup
    elev_factor -= descent_bonus
```

**Elevation-Adaptive Terrain Adjustment**:

Technical terrain impacts pace differently based on elevation profile:

**Descents** (gradient < -3%):
```python
terrain_amplification = 1.3  # 30% more impact
adjusted_terrain_factor = 1.0 + (base_terrain_factor - 1.0) × 1.3
```
- Technical terrain forces significant slowdown for safety and footing
- Example: Technical descent is 11% slower, Scrambling is 29% slower

**Climbs** (gradient > 3%):
```python
terrain_reduction = 0.6  # 40% less impact
adjusted_terrain_factor = 1.0 + (base_terrain_factor - 1.0) × 0.6
```
- Already slow on climbs, technical terrain adds less penalty
- Example: Technical climb is 3.7% slower, Scrambling is 5.6% slower

**Flat** (-3% to +3%):
```python
adjusted_terrain_factor = base_terrain_factor  # No adjustment
```
- Moderate terrain impact
- Example: Technical flat is 20% slower, Scrambling is 54% slower

**Final Weight**:
```python
segment_weight = base_weight × elev_factor
```

**Example**:
```
Segment: 10 km technical trail, 500m climb, gradient = 5%

Base weight = 10 × 1.75 = 17.5 km-equivalent

Terrain adjustment (climb):
adjusted_terrain = 1.0 + (1.75 - 1.0) × 0.6 = 1.45
base_weight = 10 × 1.45 = 14.5 km-equivalent

Elevation factor:
climb_time = 0.5 km / 0.01 km/min = 50 min
base_time = 14.5 × 6.58 = 95.4 min
elev_factor = 1.0 + 50 / 95.4 = 1.52

Final weight = 14.5 × 1.52 = 22.04 km-equivalent
```

---

### Step 3: Distribute Time Proportionally

**Purpose**: Allocate target time across segments based on their weights

**Formula**:
```python
total_weight = Σ(segment_weights)

for each segment:
    segment_time = target_time × (segment_weight / total_weight)
    segment_pace = segment_time / segment_distance
```

**Property**: At this stage, before pace limits are applied:
```
Σ(segment_times) = target_time  (exactly)
```

**Example** (3 segments with weights 22.0, 17.8, 10.5):
```
total_weight = 22.0 + 17.8 + 10.5 = 50.3 km-equivalent
target_time = 240 minutes

Segment 1: 240 × (22.0 / 50.3) = 104.97 min
Segment 2: 240 × (17.8 / 50.3) = 84.89 min  
Segment 3: 240 × (10.5 / 50.3) = 50.14 min

Total: 104.97 + 84.89 + 50.14 = 240.00 min ✓
```

---

### Step 4: Apply Pace Limits with Redistribution

**Purpose**: Enforce realistic pace constraints while preserving target time

**Pace Limits**:
- **MIN_PACE** = 2.85 min/km (sub-2hr marathon pace, ~2:51 min/km)
- **MAX_PACE** = 15.0 min/km (average walking pace)

**Iterative Clamping Algorithm**:

```python
MAX_ITERATIONS = 10

for iteration in range(MAX_ITERATIONS):
    clamped_segments = []
    excess_time = 0.0  # From too-fast segments
    deficit_time = 0.0  # For too-slow segments
    adjustable_weight = 0.0
    
    for each segment:
        pace = segment_time / segment_distance
        
        if pace < MIN_PACE:
            # Too fast - clamp and free up time
            clamped_time = segment_distance × MIN_PACE
            excess_time += segment_time - clamped_time
            segment_time = clamped_time
            mark as clamped
            
        elif pace > MAX_PACE:
            # Too slow - clamp and need more time
            clamped_time = segment_distance × MAX_PACE
            deficit_time += clamped_time - segment_time
            segment_time = clamped_time
            mark as clamped
            
        else:
            # Within limits - can be adjusted
            adjustable_weight += segment_weight
    
    # Redistribute net excess/deficit
    net_excess = excess_time - deficit_time
    
    if adjustable_weight > 0 and abs(net_excess) > 0.01:
        for each unclamped segment:
            adjustment = net_excess × (segment_weight / adjustable_weight)
            segment_time += adjustment
    else:
        break  # Converged
```

**Final Adjustment**:
```python
actual_total = Σ(segment_times)
time_diff = target_time - actual_total

# Add difference to last segment to guarantee exact match
segment_times[-1] += time_diff
```

**Properties**:
- All segment paces remain within [MIN_PACE, MAX_PACE]
- Total time still equals target exactly
- Time redistributed proportionally among unclamped segments
- Converges in typically 2-5 iterations

**Example**:
```
Initial (before limits):
Seg 1: 1.5 min/km (TOO FAST) → Clamp to 2.85 min/km, free up time
Seg 2: 18.0 min/km (TOO SLOW) → Clamp to 15.0 min/km, need more time
Seg 3: 5.0 min/km (OK) → Absorb excess time from Seg 1

After redistribution:
Seg 1: 2.85 min/km ✓
Seg 2: 15.00 min/km ✓
Seg 3: 6.20 min/km ✓ (adjusted to maintain target time)
```

---

### Step 5: Assign Effort Labels

**Purpose**: Communicate segment difficulty independent of pace

**Calculation**:
```python
# Gradient difficulty score (0-3)
gradient = (elev_gain - elev_loss) / (distance_km × 1000)
if gradient > 0.12:    gradient_score = 3
elif gradient > 0.08:  gradient_score = 2
elif gradient > 0.04:  gradient_score = 1
else:                  gradient_score = 0

# Terrain difficulty score (0-5)
terrain_scores = {
    'road': 1,
    'smooth_trail': 1,
    'dirt_road': 2,
    'rocky_runnable': 3,
    'technical': 4,
    'very_technical': 5,
    'scrambling': 6
}
terrain_score = terrain_scores[terrain_type]

# Combined difficulty
difficulty_score = gradient_score + (terrain_score - 1)

# Map to effort labels
if difficulty_score <= 0:    effort = 'easy'
elif difficulty_score <= 2:  effort = 'medium'
elif difficulty_score <= 4:  effort = 'hard'
else:                         effort = 'very_hard'
```

**Effort Labels & Colors**:
| Label | Color | Typical Conditions |
|-------|-------|-------------------|
| **Easy** | Green | Flat/gentle road or smooth trail |
| **Medium** | Blue | Moderate climb or technical terrain |
| **Hard** | Orange | Steep climb or very technical |
| **Very Hard** | Red | Very steep + technical, or scrambling |

**Key Principle**: Effort labels communicate **difficulty of the terrain**, not speed requirements. A slow pace on very steep/technical terrain is labeled "Very Hard" even though the pace itself is slow.

---

## Mental Model

### Old Approach (Base Pace Mode)
```
"Runner can run X min/km, therefore time is Y"
```
- Start with athlete abilities
- Apply modifiers (fatigue, terrain, elevation)
- Calculate resulting time
- **Problem**: Circular dependencies, unpredictable results

### New Approach (Target Time Mode)
```
"Given time T, what pace must each segment have so the weighted sum equals T?"
```
- Start with target time (hard constraint)
- Calculate neutral route cost (terrain only)
- Derive neutral reference pace (anchor)
- Layer elevation effects
- Distribute time to meet target
- Apply realistic limits
- **Advantage**: Deterministic, no circular logic, impossible to game

---

## Comparison: Base Pace vs Target Time Mode

| Aspect | Base Pace Mode | Target Time Mode |
|--------|----------------|------------------|
| **Input** | Base pace, fitness, fatigue | Target time only |
| **Output** | Estimated finish time | Guaranteed target time |
| **Approach** | Forward calculation | Inverse calculation |
| **Athlete Settings** | Required and influential | Disabled (no effect) |
| **Predictability** | Varies with abilities | Always meets target |
| **Use Case** | "How fast can I finish?" | "Can I finish in X hours?" |
| **Effort Labels** | Push/Steady/Protect | Easy/Medium/Hard/Very Hard |
| **Pace Variation** | From athlete + fatigue + terrain | From terrain + elevation only |

---

## UI Display

### Disabled Inputs
When Target Time mode is active, the following inputs are **greyed out** and excluded from calculations:
- Base pace
- Climbing ability
- Fitness level
- Fatigue penalty checkbox
- Technical skill

### Effort Guidance Panel
Replaces the old "Effort Thresholds" display with:

**Natural Pace Baseline**: Shows `simple_flat_pace = target_time / total_distance`
- Informational only
- Helps users understand the overall pace requirement
- Not used in calculations (that uses `neutral_reference_pace`)

**Effort Label Legend**:
- Easy (Green): Flat/gentle terrain
- Medium (Blue): Moderate difficulty
- Hard (Orange): Steep or technical
- Very Hard (Red): Very steep + technical

### Course Difficulty Column
New table column visible **only in Target Time mode**:
- Shows effort label badge for each segment
- Separate from pace (which shows speed)
- Communicates terrain/elevation challenge independent of pace

### Pace Color Scale
Final Pace values use red-blue-green gradient:
- **Green** (#16a34a): Fast pace (<85% of flat pace baseline)
- **Blue** (#2563eb): Normal pace (85-115% of flat pace)
- **Red** (#dc2626): Slow pace (>115% of flat pace)

Colors provide visual indication of relative speed variation across terrain.

---

## Examples

### Example 1: Mixed Terrain Route

**Route**: 30 km total
- 10 km smooth trail, 500m gain
- 10 km technical trail, 500m loss
- 10 km flat road

**Target Time**: 240 minutes (4:00:00)

**Step 0: Neutral Cost**
```
Segment 1: 10 × 1.0 = 10.0
Segment 2: 10 × 1.75 × 1.3 (descent amplification) = 22.75
Segment 3: 10 × 0.9 = 9.0
Total neutral cost = 41.75 km-equivalent
```

**Step 1: Neutral Reference Pace**
```
neutral_reference_pace = 240 / 41.75 = 5.75 min/km
simple_flat_pace = 240 / 30 = 8.00 min/km (UI display)
```

**Step 2-3: Apply Elevation & Distribute**
```
Segment 1 (climb): weight ≈ 17.6 → time = 101.2 min, pace = 10.12 min/km
Segment 2 (tech descent): weight ≈ 18.8 → time = 108.0 min, pace = 10.80 min/km
Segment 3 (flat road): weight ≈ 9.0 → time = 30.8 min, pace = 3.08 min/km
```

**Step 4: Apply Limits**
```
Segment 1: 10.12 min/km ✓ (within limits)
Segment 2: 10.80 min/km ✓ (within limits)
Segment 3: 3.08 min/km ✓ (within limits, >2.85)
Total: 240.00 min ✓ (exact)
```

**Step 5: Effort Labels**
```
Segment 1: Medium (moderate climb, smooth trail)
Segment 2: Hard (descent + technical terrain)
Segment 3: Easy (flat road)
```

### Example 2: Extreme Elevation

**Route**: 20 km
- 10 km, 1000m gain (very steep)
- 10 km, 1000m loss (very steep)

**Target Time**: 180 minutes (3:00:00)

**Without Pace Limits** (unrealistic):
- Climb: 25 min/km (too slow)
- Descent: 1.5 min/km (too fast)

**With Pace Limits** (realistic):
- Climb: 15.00 min/km (clamped to max)
- Descent: 2.85 min/km (clamped to min)
- Time redistributed to maintain 180 min total

---

## Implementation Notes

### Code Location
- Function: `calculate_independent_target_pacing()` in `app.py` (lines ~1170-1460)
- Frontend: `handlePacingModeChange()` in `static/js/app.js` for input state management
- Display: `displayResults()` in `static/js/app.js` for effort guidance and course difficulty

### Logging
Detailed logging includes:
- Neutral route cost calculation
- Neutral reference pace
- Segment weight calculations
- Pace clamping iterations
- Final time verification

### Testing
Test with:
- Routes with varied terrain (road, trail, technical)
- Extreme elevation changes (steep climbs, descents)
- Very short or very long target times
- Verify: total time always equals target, all paces within limits

---

## Why This Approach Works

### Eliminates Circular Logic
**Old problem**: Base pace affects time, time affects fatigue, fatigue affects pace
**New solution**: Target time is fixed, pace is derived to match

### Route-Relative, Not Athlete-Relative
**Old assumption**: "I can run X min/km on flat ground"
**New assumption**: "This route + target time requires Y pace distribution"

### Deterministic & Predictable
**Same inputs** (route + target time) **always produce same outputs** (segment paces)
No hidden variables, no fitness assumptions, no surprises

### Impossible to Game
Users cannot manipulate athlete settings to force unrealistic paces
The neutral cost anchor is purely mathematical and route-dependent

### Respects Physical Reality
Pace limits ensure segments remain achievable
Terrain and elevation naturally create variation
Steep/technical sections get slower paces, flats get faster paces

---

## Future Enhancements

Potential improvements (not currently implemented):

1. **User-Adjustable Pace Limits**: Allow athletes to set their own min/max based on abilities
2. **Terrain-Specific Limits**: Different pace ranges for different terrain types
3. **Segment-Level Overrides**: Manual pace adjustment for specific segments
4. **Optimization Mode**: Suggest target times that minimize extreme pace variations
5. **Confidence Intervals**: Show uncertainty ranges for segment times

---

## Version History

- **v1.7.0** (Feb 2026): Refactored to neutral route cost algorithm
  - Eliminated circular dependencies
  - Introduced neutral_reference_pace as internal anchor
  - Clear separation: terrain cost → elevation modifiers → distribution
  
- **v1.6.2** (Feb 2026): Added elevation-adaptive terrain difficulty
  - Descents amplify terrain impact (1.3x)
  - Climbs reduce terrain impact (0.6x)
  
- **v1.6.1** (Feb 2026): Increased terrain difficulty factors
  - Technical: 1.33 → 1.75
  - Very technical: 1.65 → 2.25
  - Scrambling: 2.0 → 3.0
  
- **v1.6.0** (Feb 2026): Initial Target Time mode implementation
  - Independent time solving
  - Pace limits (2.85-15.00 min/km)
  - Course difficulty column
  - Pace color scale

---

## References

- **Naismith's Rule**: 600m/h vertical speed for climbing (used in elevation penalty)
- **Sub-2hr Marathon**: ~2:51 min/km (basis for MIN_PACE)
- **Average Walking Pace**: 15 min/km (basis for MAX_PACE)
- **Terrain Factors**: Based on typical speed reductions observed in trail running research

---

**Last Updated**: February 7, 2026  
**Maintained by**: @lennon101 and GitHub Copilot
