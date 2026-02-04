#!/usr/bin/env python3
"""
Test script to verify that threshold calculation uses climbing_ability,
fitness_level, and fatigue_enabled parameters correctly.
"""

import sys
sys.path.insert(0, '/home/runner/work/RaceCraft/RaceCraft')

from app import calculate_effort_thresholds, calculate_natural_pacing, get_terrain_effort_bounds

# Create sample segments data
segments_data = [
    {'distance': 10.0, 'elev_gain': 500, 'elev_loss': 100, 'terrain_type': 'rocky_runnable'},  # Climb
    {'distance': 10.0, 'elev_gain': 100, 'elev_loss': 100, 'terrain_type': 'smooth_trail'},  # Flat
    {'distance': 10.0, 'elev_gain': 100, 'elev_loss': 500, 'terrain_type': 'rocky_runnable'},  # Descent
]

base_pace = 6.0  # 6 min/km base pace

print("Testing threshold calculation with different parameters...")
print("="*60)

# Test 1: Conservative climber vs Elite climber
print("\n1. Testing CLIMBING ABILITY impact:")
print("-" * 60)

for climbing_ability in ['conservative', 'elite']:
    # Calculate natural pacing for this climbing ability
    natural_results = calculate_natural_pacing(
        segments_data, base_pace,
        climbing_ability=climbing_ability,
        fatigue_enabled=False,
        fitness_level='recreational',
        skill_level=0.5
    )
    
    thresholds = calculate_effort_thresholds(
        natural_results, segments_data, base_pace,
        climbing_ability=climbing_ability,
        fatigue_enabled=False,
        fitness_level='recreational',
        skill_level=0.5
    )
    
    if thresholds:
        print(f"\n{climbing_ability.upper()} climber:")
        print(f"  Natural time: {thresholds['natural_time']:.2f} min")
        print(f"  Push threshold: {thresholds['push_threshold']:.2f} min")
        print(f"  Protect threshold: {thresholds['protect_threshold']:.2f} min")
        
        # Calculate percentages
        push_pct = (1 - thresholds['push_threshold'] / thresholds['natural_time']) * 100
        protect_pct = (thresholds['protect_threshold'] / thresholds['natural_time'] - 1) * 100
        print(f"  Push is {push_pct:.1f}% faster than natural")
        print(f"  Protect is {protect_pct:.1f}% slower than natural")

# Test 2: Fatigue enabled vs disabled
print("\n\n2. Testing FATIGUE impact:")
print("-" * 60)

for fatigue_enabled in [False, True]:
    # Calculate natural pacing with/without fatigue
    natural_results = calculate_natural_pacing(
        segments_data, base_pace,
        climbing_ability='moderate',
        fatigue_enabled=fatigue_enabled,
        fitness_level='recreational',
        skill_level=0.5
    )
    
    thresholds = calculate_effort_thresholds(
        natural_results, segments_data, base_pace,
        climbing_ability='moderate',
        fatigue_enabled=fatigue_enabled,
        fitness_level='recreational',
        skill_level=0.5
    )
    
    if thresholds:
        fatigue_str = "WITH" if fatigue_enabled else "WITHOUT"
        print(f"\n{fatigue_str} fatigue:")
        print(f"  Natural time: {thresholds['natural_time']:.2f} min")
        print(f"  Push threshold: {thresholds['push_threshold']:.2f} min")
        print(f"  Protect threshold: {thresholds['protect_threshold']:.2f} min")
        
        push_pct = (1 - thresholds['push_threshold'] / thresholds['natural_time']) * 100
        protect_pct = (thresholds['protect_threshold'] / thresholds['natural_time'] - 1) * 100
        print(f"  Push is {push_pct:.1f}% faster than natural")
        print(f"  Protect is {protect_pct:.1f}% slower than natural")

# Test 3: Untrained vs Elite fitness
print("\n\n3. Testing FITNESS LEVEL impact:")
print("-" * 60)

for fitness_level in ['untrained', 'elite']:
    # Calculate natural pacing for this fitness level
    natural_results = calculate_natural_pacing(
        segments_data, base_pace,
        climbing_ability='moderate',
        fatigue_enabled=False,
        fitness_level=fitness_level,
        skill_level=0.5
    )
    
    thresholds = calculate_effort_thresholds(
        natural_results, segments_data, base_pace,
        climbing_ability='moderate',
        fatigue_enabled=False,
        fitness_level=fitness_level,
        skill_level=0.5
    )
    
    if thresholds:
        print(f"\n{fitness_level.upper()} fitness:")
        print(f"  Natural time: {thresholds['natural_time']:.2f} min")
        print(f"  Push threshold: {thresholds['push_threshold']:.2f} min")
        print(f"  Protect threshold: {thresholds['protect_threshold']:.2f} min")
        
        push_pct = (1 - thresholds['push_threshold'] / thresholds['natural_time']) * 100
        protect_pct = (thresholds['protect_threshold'] / thresholds['natural_time'] - 1) * 100
        print(f"  Push is {push_pct:.1f}% faster than natural")
        print(f"  Protect is {protect_pct:.1f}% slower than natural")
        print(f"  Budget: {fitness_level == 'untrained' and '15%' or '50%'}")

print("\n" + "="*60)
print("Test complete. Thresholds SHOULD differ based on parameters.")
print("If they don't, the threshold calculation is NOT using the parameters.")
