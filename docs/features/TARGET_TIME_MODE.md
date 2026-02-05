# Target Time Mode

**Version:** v1.6.0-target-time-mode  
**Release Date:** February 2, 2026

## Overview

Target Time Mode is an inverse planning feature that allows athletes to plan their race by specifying a desired finish time instead of a base pace. The system calculates the required pacing strategy to achieve the target time while respecting physiological constraints and terrain characteristics.

### Key Concept: Forward vs. Inverse Modeling

- **Forward Model (Traditional)**: Ability → Pace → Finish Time
  - "I can run 6:00/km on flat terrain, what will my finish time be?"
  
- **Inverse Model (Target Time Mode)**: Ability + Target Time → Required Pace Strategy
  - "I want to finish in 20 hours, what pacing strategy do I need?"

## How It Works

### 1. Natural Pacing Calculation

The system first calculates **natural pacing** - what the athlete would naturally do "on autopilot" based on their abilities:

```
Natural Pacing = f(base_pace, climbing_ability, fitness_level, skill_level, terrain, fatigue)
```

This represents the predicted finish time if the athlete runs at their natural capability without any specific time goal.

### 2. Effort Allocation

The system then performs **constrained optimization** to distribute the time difference (ΔT) across segments:

```
ΔT = T_natural - T_target
```

- **ΔT > 0**: Need to go faster than natural pace (requires PUSH effort)
- **ΔT < 0**: Need to go slower than natural pace (requires PROTECT/conservation)
- **ΔT ≈ 0**: Target matches natural ability (STEADY effort)

### 3. Cost-Weighted Allocation

The optimizer distributes ΔT intelligently based on:

1. **Segment Capacity**: How much adjustment is physiologically possible
2. **Effort Cost**: How "expensive" each segment is in terms of required effort
3. **Fatigue Multiplier**: Early segments are cheaper than late segments
4. **Global Effort Budget**: Total deviation is capped by fitness level

## Effort Levels

### PUSH (Going Faster)
**Triggered when:** Segment requires ≥10% faster pace than natural

**Meaning:** This segment requires above-threshold effort to make up time. The athlete must consciously push harder than their natural pace suggests.

**Characteristics:**
- Occurs when target time is aggressive relative to natural ability
- Higher metabolic cost and fatigue accumulation
- Requires mental focus and effort discipline
- Most commonly applied to low-cost segments (flats, easy terrain)

**Example:** Natural pace is 7:00/km, required pace is 6:20/km or faster (>10% faster)

### STEADY (Natural Pace)
**Triggered when:** Segment adjustment is <10% in either direction

**Meaning:** Athlete can run at or very close to their natural pace. This is the "cruise control" effort level.

**Characteristics:**
- Sustainable, comfortable effort
- Matches athlete's natural ability for the terrain
- Minimal mental energy required
- Most efficient metabolic profile

**Example:** Natural pace is 7:00/km, required pace is 6:30-7:30/km (<10% adjustment)

### PROTECT (Going Slower)
**Triggered when:** Segment requires ≥10% slower pace than natural

**Meaning:** Athlete must actively hold back and conserve energy. This is deliberate pacing restraint.

**Characteristics:**
- Occurs when target time is conservative relative to natural ability
- Useful for ultra-distance energy management
- Requires discipline to not go too fast
- Builds energy reserves for later segments

**Example:** Natural pace is 7:00/km, required pace is 7:45/km or slower (>10% slower)

## How Athlete Abilities Affect Effort

### Climbing Ability
**Affects:** Cost of buying/saving time on climbs

- **Elite climbers**: Climbs are cheap (0.75× cost multiplier)
  - Can more easily push harder or ease back on ascents
  - Optimizer will preferentially adjust climbing segments
  
- **Conservative climbers**: Climbs are expensive (1.2× cost multiplier)
  - Harder to adjust pace on climbs
  - Optimizer will avoid aggressive climb adjustments

### Technical Skill
**Affects:** Cost and capacity on descents

- **Expert (0.8-1.0)**: Lower descent cost, wider adjustment range
  - Can safely adjust descent pace more aggressively
  - Optimizer has more flexibility on downhills
  
- **Novice (0.0-0.4)**: Higher descent cost, narrow adjustment range
  - Safety constraints limit descent adjustment
  - Even experts face hard caps on descents (risk pricing)

### Fitness Level
**Affects:** Global effort budget (total allowable deviation)

- **Elite**: 50% total deviation budget
  - Can sustain larger deviations from natural pace
  - More flexibility to hit aggressive targets
  
- **Untrained**: 15% total deviation budget
  - Limited capacity for pace adjustment
  - Aggressive targets may be unachievable

**Example:** For a 20-hour natural finish:
- Elite: Can deviate up to 10 hours total across all segments
- Untrained: Can deviate up to 3 hours total across all segments

### Fatigue (if enabled)
**Affects:** Cost multiplier increases with cumulative effort

Early segments are cheaper to adjust than late segments:
```
cost_late = cost_base × fatigue_multiplier
```

Where fatigue_multiplier grows from 1.0 (start) to 1.05-1.5 (finish) based on fitness level.

## Threshold Calculations

### Purpose
Thresholds help athletes understand their pacing options:
- **Upper threshold (PUSH)**: "If I target this time or faster, I'll need to push"
- **Lower threshold (PROTECT)**: "If I target this time or slower, I'll need to hold back"
- **Between thresholds**: Natural pacing zone (STEADY)

### Calculation Method

Thresholds are calculated using **binary search simulation** to find target times where effort transitions occur.

#### PUSH Threshold
Find the target time where **>50% of segments** require ≥10% faster adjustment.

**Algorithm:**
1. Search range: 50% to 100% of natural time
2. For each candidate target time:
   - Simulate full effort allocation
   - Count segments with ≥10% faster adjustment
3. Binary search converges when ~50% of segments hit threshold

**Interpretation:** "Target this time or faster → most segments require PUSH effort"

#### PROTECT Threshold
Find the target time where **>50% of segments** require ≥10% slower adjustment.

**Algorithm:**
1. Search range: 100% to 150% of natural time
2. For each candidate target time:
   - Simulate full effort allocation
   - Count segments with ≥10% slower adjustment
3. Binary search converges when ~50% of segments hit threshold

**Interpretation:** "Target this time or slower → most segments require PROTECT effort"

### Natural Time
The middle reference point - predicted finish time at natural pacing (no deviation).

### Including Checkpoint Time

All thresholds include total checkpoint time to represent **total race time**:
```
threshold_total = threshold_moving + (num_checkpoints × avg_cp_time)
```

This ensures thresholds match how users think about total race time (including stops).

## Practical Examples

### Example 1: Aggressive Target (PUSH Zone)

**Athlete Profile:**
- Natural finish: 20:00:00
- Fitness: Recreational
- Climbing: Moderate

**Target:** 18:00:00 (2 hours faster)

**Result:**
- ΔT = +2:00:00 (need to go faster)
- Most segments labeled PUSH (especially flats and easy terrain)
- Limited capacity: recreational fitness caps deviation at ~25% (5 hours)
- Target is achievable but requires sustained above-threshold effort

### Example 2: Conservative Target (PROTECT Zone)

**Athlete Profile:**
- Natural finish: 20:00:00
- Fitness: Trained
- Climbing: Strong

**Target:** 22:30:00 (2.5 hours slower)

**Result:**
- ΔT = -2:30:00 (need to go slower)
- Most segments labeled PROTECT
- Athlete must actively hold back, especially on climbs where they're naturally strong
- Good strategy for ultra-distance energy management

### Example 3: Optimal Target (STEADY Zone)

**Athlete Profile:**
- Natural finish: 20:00:00

**Target:** 19:45:00 to 20:15:00

**Result:**
- ΔT ≈ 0 (within ±15 minutes)
- Most/all segments labeled STEADY
- Athlete runs at natural ability without significant deviation
- Most sustainable and lowest-risk pacing strategy

## Constraints and Limitations

### Segment-Level Constraints
Each segment has terrain-specific bounds on adjustment:

- **Steep climbs**: Wider range for strong climbers, narrow for conservative
- **Descents**: Hard caps even for skilled athletes (safety/risk limits)
- **Flat terrain**: Medium range, less ability-dependent

### Global Constraints
- **Fitness budget**: Total deviation capped by fitness level
- **Fatigue cost**: Late-race adjustments are more expensive
- **Capacity limits**: Can't exceed physiological boundaries

### When Targets Are Unachievable

If target requires more deviation than fitness budget allows:
```
required_deviation > (natural_time × fitness_budget)
```

The system caps the deviation and warns the user. The calculated plan will get as close as possible but won't fully achieve the target.

## UI Indicators

The elevation profile chart displays effort zones:
- 🔴 **Red segments**: PUSH effort required
- 🟢 **Green segments**: STEADY effort (natural pace)
- 🔵 **Blue segments**: PROTECT effort required

Thresholds are shown in the target time input:
```
Thresholds: Push <18:30:00 | Natural: 20:00:00 | Protect >21:30:00
```

## Comparison with Pace-Based Mode

| Aspect | Pace-Based Mode | Target Time Mode |
|--------|----------------|------------------|
| **Input** | Flat pace (min/km) | Total finish time |
| **Output** | Predicted finish time | Required pace strategy |
| **Model** | Forward (ability → time) | Inverse (time → effort) |
| **Effort** | Implicit | Explicit (labeled) |
| **Optimization** | None | Cost-weighted allocation |
| **Use Case** | "What can I do?" | "What must I do?" |

## Best Practices

### 1. Start with Natural Time
- Calculate with your actual abilities first
- See what your natural finish time would be
- Use this as a reality check for targets

### 2. Respect Thresholds
- **Between thresholds**: Safest, most sustainable pacing
- **At PUSH threshold**: Requires good fitness and pacing discipline
- **At PROTECT threshold**: Good for ultra-distance or learning races

### 3. Consider Your Experience
- **First-time distance**: Target PROTECT zone (conservative)
- **Experienced**: Target between STEADY and PUSH threshold
- **Peak performance**: Target PUSH zone (requires perfect execution)

### 4. Account for Checkpoint Time
- Don't forget to include realistic aid station time
- More checkpoints = more total time added
- Thresholds automatically include this

### 5. Trust the Labels
- **PUSH**: Expect to feel challenged, monitor for overexertion
- **STEADY**: Should feel sustainable and controlled
- **PROTECT**: Should feel easy, resist urge to go faster

## Technical Notes

### Optimization Algorithm
The effort allocator uses a **greedy cost-weighted distribution** rather than true mathematical optimization. This provides:
- Fast computation (no iterative solving)
- Intuitive results (prioritizes easy terrain)
- Respect for hard constraints (physiological limits)

### Assumptions
1. Athlete maintains target pacing strategy throughout race
2. Conditions match those modeled (weather, terrain, etc.)
3. Nutrition and hydration are adequate (no bonking)
4. No mechanical issues or unplanned stops

### Limitations
- Cannot account for unknown race day conditions
- Assumes rational pacing (no emotion-driven surges)
- Simplified fatigue model (actual fatigue is complex)
- Does not model non-physiological slowdowns (navigation, gear, etc.)

## Version History

- **v1.6.0-target-time-mode** (Feb 2, 2026): Initial release
  - Target time input mode
  - Effort level calculation (PUSH/STEADY/PROTECT)
  - Threshold calculation using binary search
  - Ability-aware cost weighting
  - Checkpoint time integration

## See Also

- [FATIGUE_MODEL.md](../models/FATIGUE_MODEL.md) - Fatigue calculation details
- [CLIMBING_MODEL.md](../models/CLIMBING_MODEL.md) - Climbing pace model
- [TERRAIN_DIFFICULTY.md](../models/TERRAIN_DIFFICULTY.md) - Terrain efficiency factors
