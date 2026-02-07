# Distance-Adaptive Base Pace Estimation

## Overview

RaceCraft now supports **automatic base pace calculation** from known race performances. This feature uses scientifically validated performance prediction models to estimate an appropriate base pace for your target race distance.

## How It Works

### 1. Riegel's Formula

The system uses **Riegel's formula** to predict race times across different distances:

```
Time₂ = Time₁ × (Distance₂ / Distance₁)^1.06
```

Where:
- `Time₁` = Your known race time
- `Distance₁` = Your known race distance
- `Time₂` = Predicted time for new distance
- `Distance₂` = Target race distance
- `1.06` = Fatigue exponent (empirically validated)

### 2. Ultra-Distance Intensity Downshift

For races **longer than 42.2 km** (marathon), an additional intensity reduction is applied:

```
intensity_factor = 1.0 - log₁₀(effort_ratio) × 0.15
adjusted_time = predicted_time / intensity_factor
```

Where:
- `effort_ratio` = target_distance / reference_distance
- `0.15` = Downshift coefficient (calibrated from ultra-marathon data)

This accounts for the more conservative pacing required in ultra-distance events:
- 2× distance increase → ~4.5% slower pace
- 4× distance increase → ~9% slower pace  
- 10× distance increase → ~15% slower pace

### 3. Base Pace Calculation

The final base pace is calculated as:

```
base_pace = adjusted_time / target_distance
```

This pace serves as the **flat terrain baseline** for all subsequent elevation and terrain adjustments in RaceCraft's pacing model.

## Usage

### Step 1: Upload Your GPX Route

Upload your race GPX file to determine the target distance.

### Step 2: Select "From Performance"

In the **Pacing** section, toggle to "From Performance" mode.

### Step 3: Enter Your Reference Performance

1. **Distance**: Select from common race distances or enter custom distance
   - 5K, 10K, 15K, Half Marathon, Marathon, 50K
   - Custom: Any distance from 1-500 km

2. **Time**: Enter your race finish time (HH:MM:SS)
   - Example: 10K in 45:00 → enter 0:45:00

### Step 4: Calculate Estimated Pace

Click **"Calculate Estimated Pace"** to see:
- Estimated base pace (min/km)
- Predicted finish time for target distance
- Whether ultra-distance downshift was applied

### Step 5: Use the Estimated Pace

Click **"Use This Pace"** to:
- Apply the estimated pace to your race plan
- Switch back to manual entry mode (allowing adjustments)
- Proceed with normal race plan calculation

## Examples

### Example 1: 10K → 50K Ultra

**Input:**
- Reference: 10K in 45:00 (4:30 min/km pace)
- Target: 50K route

**Calculation:**
1. Riegel prediction: 247.8 minutes (4:55 min/km)
2. Ultra downshift: +11.7% → 276.8 minutes (5:32 min/km)
3. **Result: 5:32 min/km base pace**

### Example 2: Half Marathon → 100K Ultra

**Input:**
- Reference: Half Marathon in 1:30:00 (4:16 min/km pace)
- Target: 100K route

**Calculation:**
1. Riegel prediction: 449.2 minutes (4:30 min/km)
2. Ultra downshift: +6.0% → 475.9 minutes (4:46 min/km)
3. **Result: 4:46 min/km base pace**

### Example 3: 10K → Marathon

**Input:**
- Reference: 10K in 40:00 (4:00 min/km pace)
- Target: Marathon (42.2 km)

**Calculation:**
1. Riegel prediction: 183.9 minutes (4:21 min/km)
2. No ultra downshift (marathon is standard distance)
3. **Result: 4:21 min/km base pace**

## When to Use This Feature

### ✅ Good Use Cases

- Planning for a longer race than you've raced before
- Estimating pace for a new ultra distance
- Converting recent race performance to race plan
- Starting point when unsure of sustainable pace

### ⚠️ Limitations

- Assumes similar terrain and conditions
- May not account for course-specific difficulty
- Works best with recent performances (within 3-6 months)
- Less accurate for very large distance jumps (>10×)

## Tips for Accuracy

1. **Use Recent Performances**: Performance within the last 3-6 months
2. **Choose Similar Terrain**: Road race → road race, trail → trail
3. **Consider Fitness Changes**: Adjust if training has significantly changed
4. **Start Conservative**: For first ultra, consider adding 5-10% to estimated pace
5. **Validate with Known Data**: If you have multiple race times, check consistency

## Scientific Background

### Riegel's Formula Validation

Riegel's formula (1981) has been validated across:
- Distance range: 5K to ultra-marathons
- Various athlete levels: recreational to elite
- Multiple studies confirming 1.06 exponent accuracy

### Ultra-Distance Modifications

The intensity downshift model is based on:
- Ultra-marathon performance research (Hoffman, 2010)
- Western States 100 completion data
- UTMB and similar ultra-distance events
- Empirical observation: ~15% pace reduction per 10× distance

## Integration with RaceCraft Models

The estimated base pace integrates seamlessly with:
- **Elevation Adjustments**: Vertical speed climbing model
- **Terrain Difficulty**: Technical terrain multipliers
- **Fatigue Model**: Cumulative effort degradation
- **All Other Features**: Nutrition, checkpoints, drop bags

## References

- Riegel, P. (1981). Athletic records and human endurance. American Scientist.
- Hoffman, M. D. (2010). Performance trends in 161-km ultramarathons. International Journal of Sports Medicine.
- RaceCraft Documentation: Climbing Model, Fatigue Model, Terrain Difficulty

---

**Version**: v1.7.0  
**Last Updated**: February 7, 2026
