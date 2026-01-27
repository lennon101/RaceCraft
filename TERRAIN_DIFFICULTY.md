# Terrain Difficulty Model

RaceCraft uses a sophisticated terrain difficulty system that models how different trail surfaces and technical features affect running pace. Unlike simple time penalties, terrain difficulty is implemented as a **local, immediate efficiency penalty** that affects segment speed without altering fatigue accumulation.

## Overview

The terrain model recognizes that technical terrain slows runners down independently of fitness or fatigue. A fresh runner on rocky terrain will be slower than on smooth trail, and a fatigued runner on rocky terrain will experience the same terrain-induced slowdown plus their fatigue penalty.

### Key Principles

1. **Terrain affects speed, not fatigue**: Terrain difficulty multiplies segment time but does NOT affect when fatigue kicks in or how fast it accumulates
2. **Separate from gradient**: Terrain and elevation changes are independent factors - steep smooth trail is different from flat technical trail
3. **Skill-dependent**: Technical skill reduces terrain penalties, representing experienced trail runners' ability to navigate obstacles efficiently
4. **Gradient-scaled**: Terrain effects amplify on steeper grades (both up and down)
5. **Descent-weighted**: Terrain impacts descents more than climbs (braking and foot placement are more critical downhill)

## Terrain Efficiency Factor (TEF)

The core of the model is the Terrain Efficiency Factor (TEF), a multiplier applied to segment time:

```
segment_time = base_time × terrain_factor × fatigue_multiplier
```

Where:
- **base_time**: Time to cover segment based on Z2 pace and elevation adjustments
- **terrain_factor**: TEF from terrain model (≥ 1.0)
- **fatigue_multiplier**: Separate fatigue penalty based on cumulative effort

## Terrain Types and Baseline Factors

RaceCraft includes 7 terrain types with scientifically-derived baseline multipliers:

| Terrain Type | Factor | Description | Example |
|--------------|--------|-------------|---------|
| **Road/Track** | 0.95× | Paved or groomed surfaces | Roads, athletics tracks |
| **Smooth Trail** | 1.00× | Ideal baseline trail | Well-maintained singletrack, fire roads |
| **Dirt Road** | 1.05× | Unpaved roads, double track | Jeep trails, dirt roads |
| **Rocky Runnable** | 1.15× | Rocky but continuously runnable | Alpine trails with rock gardens |
| **Technical Trail** | 1.33× | Roots, rocks requiring care | Typical technical singletrack |
| **Very Technical** | 1.65× | Hands-on-knees terrain | Steep rock sections, major obstacles |
| **Scrambling** | 2.00× | Unstable footing, route-finding | Talus fields, boulder scrambles |

### Factor Interpretation

A terrain factor of 1.33× means the terrain makes you 33% slower compared to smooth trail at the same gradient and effort level. For example:
- Smooth trail at 6:00/km → Technical trail at 7:58/km
- This is before gradient effects or skill adjustments

## Gradient Scaling

Terrain effects become more pronounced on steeper terrain. The model applies gradient scaling:

```
effective_terrain_factor = terrain_factor × (1 + γ × |gradient|)
```

Where:
- **γ (gamma)**: Gradient scaling coefficient = 1.25
- **gradient**: Net grade as decimal (e.g., 0.10 = 10% grade)

### Example

Technical trail (base factor 1.33×) on 10% grade:
```
effective_factor = 1.33 × (1 + 1.25 × 0.10)
                = 1.33 × 1.125
                = 1.496×
```

The terrain penalty increases from 33% to 49.6% due to the steep grade.

### Rationale

Steeper terrain amplifies technical difficulty because:
- Uphill: Harder to maintain line, more precise foot placement needed
- Downhill: Greater braking forces, more consequence for missteps
- Both: Reduced margin for error increases time cost of obstacles

## Climb vs Descent Differential

Terrain affects descents more severely than climbs:

- **Descents**: 100% terrain effect
- **Climbs**: 70% terrain effect

This reflects the reality that:
- Descending technical terrain requires constant braking and precise foot placement
- Ascending technical terrain allows more careful, deliberate movement
- Downhill speed amplifies consequences of mistakes

### Example

Very technical terrain (1.65× base factor):
- **On descent**: Full 1.65× penalty applied
- **On climb**: Only 1.455× penalty (70% effect)

The formula:
```python
if is_descent:
    direction_adjusted = 1 + (scaled_factor - 1) × 1.0
else:  # climb
    direction_adjusted = 1 + (scaled_factor - 1) × 0.7
```

## Technical Skill Adjustment

Athletes with better technical skills navigate difficult terrain faster. The skill parameter ranges from 0 (novice) to 1 (expert):

```
skill_adjusted_factor = 1 + (direction_adjusted_factor - 1) × (1 - skill)
```

### Skill Levels

| Skill Level | Value | Terrain Penalty | Description |
|-------------|-------|-----------------|-------------|
| **Novice** | 0.0 | 100% | New to trail running |
| **Beginner** | 0.25 | 75% | Some trail experience |
| **Intermediate** | 0.5 | 50% | Regular trail runner |
| **Advanced** | 0.75 | 25% | Experienced technical runner |
| **Expert** | 1.0 | 0% | Elite mountain/ultra runner |

### Example

Technical trail (1.33× base) with intermediate skill (0.5):
```
adjusted_factor = 1 + (1.33 - 1) × (1 - 0.5)
                = 1 + 0.33 × 0.5
                = 1.165×
```

The runner experiences only 16.5% slowdown instead of 33% due to their technical proficiency.

### Interpretation

An expert trail runner (skill = 1.0) on technical terrain runs at the same pace as if it were smooth trail - they've mastered the technique so well that terrain no longer slows them down. Meanwhile, a novice (skill = 0.0) experiences the full terrain penalty.

## Complete Calculation Flow

The full terrain efficiency factor calculation combines all components:

### Step 1: Base Terrain Factor
Select terrain type → get base factor (e.g., Technical Trail = 1.33×)

### Step 2: Gradient Scaling
```
scaled_factor = base_factor × (1 + γ × |gradient|)
```

### Step 3: Descent/Climb Adjustment
```
if elevation_loss > elevation_gain:
    direction_factor = 1 + (scaled_factor - 1) × 1.0  # descent
else:
    direction_factor = 1 + (scaled_factor - 1) × 0.7  # climb
```

### Step 4: Skill Adjustment
```
final_factor = 1 + (direction_factor - 1) × (1 - skill_level)
```

### Step 5: Apply to Segment Time
```
adjusted_time = base_segment_time × final_factor × fatigue_multiplier
```

## Worked Example

**Scenario**: Technical trail segment
- Distance: 5 km
- Net elevation: -200m (descent)
- Average gradient: -4%
- Base pace: 6:00/km (no elevation)
- After elevation adjustment: 5:30/km (downhill benefit)
- Skill level: Intermediate (0.5)
- No fatigue yet (multiplier = 1.0)

**Calculation**:

1. **Base terrain factor**: Technical Trail = 1.33×

2. **Gradient scaling**:
   ```
   scaled = 1.33 × (1 + 1.25 × 0.04)
          = 1.33 × 1.05
          = 1.397×
   ```

3. **Descent adjustment** (100% effect):
   ```
   direction = 1 + (1.397 - 1) × 1.0
             = 1.397×
   ```

4. **Skill adjustment** (intermediate):
   ```
   final = 1 + (1.397 - 1) × (1 - 0.5)
         = 1 + 0.397 × 0.5
         = 1.198×
   ```

5. **Apply to segment**:
   ```
   base_time = 5 km × 5:30/km = 27:30
   terrain_adjusted = 27:30 × 1.198 = 32:57
   final_pace = 32:57 / 5 km = 6:35/km
   ```

**Result**: Despite the downhill advantage (5:30/km elevation-adjusted pace), the technical terrain slows the runner to 6:35/km - slower than their flat pace. A novice runner would be at 7:28/km on the same segment.

## Integration with Fatigue Model

The terrain system operates **independently** of the fatigue model:

### Fatigue Calculations (Unchanged)
```
effort_km = distance + ascent/100 + descent/200
cumulative_effort += segment_effort
if cumulative_effort > FOP:
    fatigue_multiplier = 1 + α × ((E - FOP) / FOP)^β
```

### Combined Effect
```
final_pace = base_pace × terrain_factor × fatigue_multiplier
```

**Key Point**: Terrain difficulty does NOT:
- Change when fatigue starts (FOP remains the same)
- Affect how fast fatigue accumulates (effort calculation unchanged)
- Compound with fatigue exponentially (multipliers are independent)

A runner with 30% terrain penalty and 20% fatigue penalty experiences:
```
1.30 × 1.20 = 1.56× total slowdown (56% slower than base)
```

NOT: 50% slower (30% + 20%)

## Usage Guidelines

### Choosing Terrain Type

Consider the **predominant surface** and **technical demands** of each segment:

- **Road/Track**: Almost entirely paved, no obstacles
- **Smooth Trail**: Well-maintained, minimal obstacles, good footing
- **Dirt Road**: Unpaved but wide, minimal technical features
- **Rocky Runnable**: Rocks/roots present but continuous running possible
- **Technical Trail**: Frequent obstacles requiring focus and adjustment
- **Very Technical**: Regular need to use hands, careful foot placement
- **Scrambling**: Route-finding, boulder hopping, significant exposure

### Setting Skill Level

Be honest about technical ability:

- **Novice**: First trail race, limited technical experience
- **Beginner**: 1-2 years trail running, comfortable on moderate terrain
- **Intermediate**: Regular trail racer, confident on most technical terrain
- **Advanced**: Experienced mountain runner, rarely slowed by terrain
- **Expert**: Elite level, technical sections are not a limiting factor

### Tips for Accuracy

1. **Be conservative early in plan development**: Overestimate terrain difficulty for unfamiliar courses
2. **Adjust after reconnaissance**: Update terrain types after course preview
3. **Consider conditions**: Wet/muddy conditions may warrant upgrading terrain type
4. **Segment appropriately**: Break course into segments with similar terrain characteristics
5. **Don't overthink it**: Small errors in terrain type have minimal impact on overall plan

## Model Validation and Tuning

The terrain factors are derived from:
- Field data from trail running studies
- Analysis of professional ultra-runner splits
- Comparison of road vs trail pace ratios
- Trail running community feedback

### Adjusting Parameters (Advanced)

If you need to tune the model for your specific conditions, the key parameters in `app.py` are:

```python
TERRAIN_FACTORS = {
    'road': 0.95,
    'smooth_trail': 1.0,
    'dirt_road': 1.05,
    'rocky_runnable': 1.15,
    'technical': 1.325,
    'very_technical': 1.65,
    'scrambling': 2.0
}

TERRAIN_GRADIENT_GAMMA = 1.25    # How much gradient amplifies terrain
TERRAIN_CLIMB_FACTOR = 0.7       # Terrain effect on climbs (0.0-1.0)
TERRAIN_DESCENT_FACTOR = 1.0     # Terrain effect on descents (0.0-1.0)
```

## Comparison to Old System

The previous system used simple time additions:
- Easy (road): -10 seconds/km
- Normal: 0 seconds/km
- Difficult: +10s/km uphill, +20s/km downhill

**Limitations of old system**:
- Fixed penalties regardless of gradient
- No skill adjustment
- Only 3 categories
- Inconsistent with fatigue model

**New system advantages**:
- Multiplicative (scales with pace and fatigue)
- Gradient-aware
- Skill-adjustable
- 7 detailed terrain types
- Mathematically consistent with other penalties
- Better represents real-world running biomechanics

## See Also

- [Fatigue Model Documentation](FATIGUE_MODEL.md) - Understanding cumulative effort and fatigue onset
- [Main README](README.md) - General application usage and features

## References

The terrain model is based on research and practical experience in:
- Mountain and ultra running physiology
- Trail running pace analysis
- Biomechanical studies of running on varied surfaces
- Elite athlete training and racing data

For questions or suggestions about the terrain model, please open an issue on the project repository.
