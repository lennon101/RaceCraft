"""
Test script to verify the new climbing model calculations.
"""

# Test the climbing model functions
print("=" * 60)
print("CLIMBING MODEL VERIFICATION")
print("=" * 60)

# Simulate the constants and functions from app.py
CLIMBING_ABILITY_PARAMS = {
    'conservative': {'vertical_speed': 500, 'label': 'Conservative Climber'},
    'moderate': {'vertical_speed': 700, 'label': 'Moderate Climber'},
    'strong': {'vertical_speed': 900, 'label': 'Strong Climber'},
    'very_strong': {'vertical_speed': 1100, 'label': 'Very Strong Climber'},
    'elite': {'vertical_speed': 1300, 'label': 'Elite Climber'}
}

def calculate_vertical_speed(base_vertical_speed, gradient):
    """Calculate gradient-aware vertical speed in m/h."""
    gradient_pct = abs(gradient) * 100.0
    
    if gradient_pct < 5.0:
        efficiency = 0.60
    elif gradient_pct < 8.0:
        efficiency = 0.60 + (gradient_pct - 5.0) / 3.0 * 0.40
    elif gradient_pct <= 12.0:
        efficiency = 1.0
    elif gradient_pct <= 15.0:
        efficiency = 1.0 - (gradient_pct - 12.0) / 3.0 * 0.15
    elif gradient_pct <= 20.0:
        efficiency = 0.85 - (gradient_pct - 15.0) / 5.0 * 0.20
    else:
        efficiency = 0.65
    
    return base_vertical_speed * efficiency

def calculate_downhill_multiplier(gradient, terrain_type='smooth_trail'):
    """Calculate downhill speed multiplier based on gradient."""
    if gradient >= 0:
        return 1.0
    
    gradient_pct = abs(gradient) * 100.0
    
    if gradient_pct <= 5.0:
        base_multiplier = 1.05
    elif gradient_pct <= 10.0:
        base_multiplier = 1.15
    elif gradient_pct <= 15.0:
        base_multiplier = 1.20
    else:
        base_multiplier = 1.10
    
    terrain_downhill_caps = {
        'road': 1.0,
        'smooth_trail': 0.95,
        'dirt_road': 0.90,
        'rocky_runnable': 0.80,
        'technical': 0.70,
        'very_technical': 0.60,
        'scrambling': 0.50
    }
    
    terrain_cap = terrain_downhill_caps.get(terrain_type, 0.90)
    adjusted_multiplier = 1.0 + (base_multiplier - 1.0) * terrain_cap
    
    return adjusted_multiplier

# Test scenarios
print("\n1. GRADIENT-AWARE VERTICAL SPEED")
print("-" * 60)
base_vs = 700  # Moderate climber
gradients = [0.03, 0.05, 0.08, 0.10, 0.12, 0.15, 0.18, 0.25]

for grad in gradients:
    adj_vs = calculate_vertical_speed(base_vs, grad)
    efficiency = (adj_vs / base_vs) * 100
    print(f"Gradient {grad*100:5.1f}%: {adj_vs:6.1f} m/h ({efficiency:5.1f}% efficiency)")

print("\n2. CLIMBING TIME CALCULATION")
print("-" * 60)
# Example: 5 km segment with 500m climb
distance_km = 5.0
ascent_m = 500
base_pace = 6.5  # min/km flat

print(f"Segment: {distance_km} km, {ascent_m}m climb")
print(f"Flat pace: {base_pace:.1f} min/km")
print()

for ability, params in CLIMBING_ABILITY_PARAMS.items():
    vs = params['vertical_speed']
    flat_speed_kmh = 60.0 / base_pace
    
    # Calculate times
    horizontal_time = (distance_km / flat_speed_kmh) * 60.0
    climb_time = (ascent_m / vs) * 60.0
    total_time = horizontal_time + climb_time
    pace = total_time / distance_km
    
    print(f"{params['label']:25s} ({vs:4d} m/h):")
    print(f"  Horizontal: {horizontal_time:5.1f} min | Climb: {climb_time:5.1f} min")
    print(f"  Total: {total_time:5.1f} min | Pace: {int(pace):2d}:{int((pace%1)*60):02d} min/km")
    print()

print("\n3. DOWNHILL SPEED MULTIPLIERS")
print("-" * 60)
gradients = [-0.03, -0.05, -0.08, -0.10, -0.12, -0.15, -0.18]
terrains = ['smooth_trail', 'technical']

for terrain in terrains:
    print(f"\nTerrain: {terrain}")
    for grad in gradients:
        mult = calculate_downhill_multiplier(grad, terrain)
        speedup_pct = (mult - 1.0) * 100
        print(f"  Gradient {grad*100:6.1f}%: {mult:.3f}× ({speedup_pct:+5.1f}%)")

print("\n4. INTEGRATION TEST: Complete Segment Calculation")
print("-" * 60)
# Realistic mountain segment
distance_km = 3.0
ascent_m = 300
descent_m = 50
base_pace = 6.5
climbing_ability = 'moderate'
terrain_factor = 1.33  # Technical trail
fatigue_multiplier = 1.15  # Late in race

vs = CLIMBING_ABILITY_PARAMS[climbing_ability]['vertical_speed']
gradient = (ascent_m - descent_m) / (distance_km * 1000.0)

print(f"Segment: {distance_km} km, +{ascent_m}m, -{descent_m}m")
print(f"Climbing ability: {climbing_ability} ({vs} m/h)")
print(f"Terrain factor: {terrain_factor:.2f}×")
print(f"Fatigue multiplier: {fatigue_multiplier:.2f}×")
print()

# Calculate
flat_speed_kmh = 60.0 / base_pace
horizontal_time = (distance_km / flat_speed_kmh) * 60.0
climb_time = (ascent_m / vs) * 60.0
base_time = horizontal_time + climb_time

print(f"1. Horizontal time: {horizontal_time:.1f} min")
print(f"2. Climb time: {climb_time:.1f} min")
print(f"3. Base time: {base_time:.1f} min")
print(f"4. With terrain: {base_time * terrain_factor:.1f} min")
print(f"5. With fatigue: {base_time * terrain_factor * fatigue_multiplier:.1f} min")
print()

final_time = base_time * terrain_factor * fatigue_multiplier
final_pace = final_time / distance_km
print(f"Final pace: {int(final_pace):2d}:{int((final_pace%1)*60):02d} min/km")
print(f"Segment time: {int(final_time//60):2d}h {int(final_time%60):02d}m")

print("\n" + "=" * 60)
print("VERIFICATION COMPLETE")
print("=" * 60)
