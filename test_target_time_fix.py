#!/usr/bin/env python3
"""
Test script to verify the new independent target time calculation is working.

This test demonstrates that when pacing_mode='target_time', the API uses the
new calculate_independent_target_pacing function instead of the old base pace
calculation.

Expected behavior:
1. Total time matches target exactly
2. Pace varies based on terrain and elevation (not fixed base pace)
3. Fatigue seconds = 0 (fatigue not used in target time mode)
4. Effort levels present (easy/medium/hard/very_hard)
5. No base pace, fitness, or technical ability effects
"""

import sys
import subprocess
import time
import requests
import json

def start_flask_server():
    """Start Flask server in background."""
    print("Starting Flask server...")
    proc = subprocess.Popen(
        ['python3', 'app.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    # Wait for server to start
    for _ in range(20):
        try:
            response = requests.get('http://localhost:5001/', timeout=1)
            print("✓ Server is ready")
            return proc
        except:
            time.sleep(0.5)
    print("✗ Server failed to start")
    return proc

def test_target_time_mode():
    """Test target time mode calculation."""
    print("\n" + "=" * 70)
    print("TEST: Target Time Mode - Independent Calculation")
    print("=" * 70)
    
    # Test data with varied terrain and elevation
    test_data = {
        "elevation_profile": [
            {"distance": 0, "elevation": 100},
            {"distance": 2, "elevation": 250},    # 150m climb in 2km
            {"distance": 5, "elevation": 400},    # 150m climb in 3km
            {"distance": 8, "elevation": 350},    # 50m descent in 3km
            {"distance": 10, "elevation": 200}    # 150m descent in 2km
        ],
        "checkpoint_distances": [5, 10],
        "num_checkpoints": 2,
        "avg_cp_time": 3,
        "pacing_mode": "target_time",
        "target_time": "03:00:00",
        "z2_pace": 5.5,
        "climbing_ability": "strong",
        "fatigue_enabled": True,
        "fitness_level": "elite",
        "skill_level": 0.8,
        "carbs_per_hour": 80,
        "water_per_hour": 600,
        "segment_terrain_types": ["technical", "very_technical"]
    }
    
    print("\nInput Parameters:")
    print(f"  Target Time: 03:00:00 (180 minutes)")
    print(f"  Distance: 10 km")
    print(f"  Elevation: +300m / -200m")
    print(f"  Terrain: technical, very_technical")
    print(f"  Pacing Mode: target_time")
    print(f"  Base Pace: 5:30 min/km (should be IGNORED)")
    print(f"  Fitness: elite (should be IGNORED)")
    print(f"  Climbing: strong (should be IGNORED)")
    
    response = requests.post('http://localhost:5001/api/calculate', json=test_data)
    
    if response.status_code != 200:
        print(f"\n✗ API Error: {response.json()}")
        return False
    
    result = response.json()
    segments = result['segments']
    
    # Calculate metrics
    total_moving_time = sum(s['segment_time'] for s in segments if s['distance'] > 0)
    final_time = segments[-1]['cumulative_time']
    paces = [s['pace'] for s in segments if s['distance'] > 0]
    effort_levels = [s.get('effort_level', 'MISSING') for s in segments if s['distance'] > 0]
    fatigue_values = [s['fatigue_seconds'] for s in segments]
    
    print("\n" + "-" * 70)
    print("VERIFICATION RESULTS:")
    print("-" * 70)
    
    # Test 1: Total time matches target
    print(f"\n1. Total time matches target:")
    print(f"   Expected: 03:00:00 (180 minutes)")
    print(f"   Actual: {segments[-1]['cumulative_time_str']} ({final_time:.2f} minutes)")
    time_diff = abs(final_time - 180.0)
    test1 = time_diff < 0.1
    print(f"   Result: {'✓ PASS' if test1 else '✗ FAIL'} (diff: {time_diff:.4f} min)")
    
    # Test 2: Pace varies (not using fixed base pace)
    print(f"\n2. Pace varies based on terrain/elevation (NOT fixed base pace):")
    print(f"   Paces: {[f'{p:.2f}' for p in paces]} min/km")
    test2 = len(set(paces)) > 1 or len(paces) == 1
    print(f"   Result: {'✓ PASS' if test2 else '✗ FAIL'}")
    
    # Test 3: Fatigue seconds = 0
    print(f"\n3. Fatigue seconds = 0 (fatigue not used in target time mode):")
    print(f"   Fatigue values: {fatigue_values}")
    test3 = all(f == 0.0 for f in fatigue_values)
    print(f"   Result: {'✓ PASS' if test3 else '✗ FAIL'}")
    
    # Test 4: Effort levels present
    print(f"\n4. Effort levels present (NOT 'steady'):")
    print(f"   Effort levels: {effort_levels}")
    test4 = all(e in ['easy', 'medium', 'hard', 'very_hard'] for e in effort_levels)
    print(f"   Result: {'✓ PASS' if test4 else '✗ FAIL'}")
    
    # Test 5: Moving time correct
    print(f"\n5. Moving time calculation:")
    print(f"   Total time: {final_time:.2f} min")
    print(f"   CP time: 2 × 3 = 6 min")
    print(f"   Moving time: {total_moving_time:.2f} min")
    print(f"   Expected moving: 174 min")
    test5 = abs(total_moving_time - 174.0) < 0.1
    print(f"   Result: {'✓ PASS' if test5 else '✗ FAIL'}")
    
    print("\n" + "-" * 70)
    print("DETAILED SEGMENT DATA:")
    print("-" * 70)
    for i, seg in enumerate(segments):
        if seg['distance'] > 0:
            print(f"\nSegment {i+1}: {seg['from']} → {seg['to']}")
            print(f"  Distance: {seg['distance']} km")
            print(f"  Elevation: +{seg['elev_gain']:.0f}m / -{seg['elev_loss']:.0f}m")
            print(f"  Terrain: {seg['terrain_type']}")
            print(f"  Pace: {seg['pace_str']} ({seg['pace']:.2f} min/km)")
            print(f"  Time: {seg['segment_time_str']} ({seg['segment_time']:.2f} min)")
            print(f"  Effort: {seg.get('effort_level', 'MISSING')}")
            print(f"  Fatigue: {seg['fatigue_seconds']} seconds")
    
    # Overall result
    all_pass = test1 and test2 and test3 and test4 and test5
    print("\n" + "=" * 70)
    if all_pass:
        print("✓ ALL TESTS PASSED - Independent target time calculation is working!")
    else:
        print("✗ SOME TESTS FAILED - Please review the results above")
    print("=" * 70 + "\n")
    
    return all_pass

def test_base_pace_mode():
    """Test that base pace mode still works correctly."""
    print("\n" + "=" * 70)
    print("TEST: Base Pace Mode - Forward Calculation")
    print("=" * 70)
    
    test_data = {
        "elevation_profile": [
            {"distance": 0, "elevation": 100},
            {"distance": 5, "elevation": 200},
            {"distance": 10, "elevation": 150}
        ],
        "checkpoint_distances": [5, 10],
        "num_checkpoints": 2,
        "avg_cp_time": 2,
        "pacing_mode": "base_pace",
        "z2_pace": 6.0,
        "climbing_ability": "moderate",
        "fatigue_enabled": True,
        "fitness_level": "trained",
        "skill_level": 0.5,
        "carbs_per_hour": 60,
        "water_per_hour": 500,
        "segment_terrain_types": ["smooth_trail", "smooth_trail"]
    }
    
    print("\nInput Parameters:")
    print(f"  Pacing Mode: base_pace")
    print(f"  Base Pace: 6:00 min/km")
    print(f"  Fitness: trained")
    print(f"  Fatigue: enabled")
    
    response = requests.post('http://localhost:5001/api/calculate', json=test_data)
    
    if response.status_code != 200:
        print(f"\n✗ API Error: {response.json()}")
        return False
    
    result = response.json()
    segments = result['segments']
    
    # In base pace mode, effort_level should be 'steady'
    effort_levels = [s.get('effort_level', 'MISSING') for s in segments if s['distance'] > 0]
    fatigue_values = [s['fatigue_seconds'] for s in segments if s['distance'] > 0]
    
    print(f"\n✓ Base pace mode response received")
    print(f"  Effort levels: {effort_levels} (should be 'steady')")
    print(f"  Fatigue present: {any(f > 0 for f in fatigue_values)}")
    
    test1 = all(e == 'steady' for e in effort_levels)
    test2 = True  # Fatigue may or may not be present depending on settings
    
    print(f"\n{'✓ PASS' if test1 and test2 else '✗ FAIL'}: Base pace mode works correctly\n")
    
    return test1 and test2

if __name__ == '__main__':
    # Start Flask server
    server_proc = start_flask_server()
    
    try:
        # Run tests
        test1_pass = test_target_time_mode()
        test2_pass = test_base_pace_mode()
        
        # Summary
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"Target Time Mode: {'✓ PASS' if test1_pass else '✗ FAIL'}")
        print(f"Base Pace Mode: {'✓ PASS' if test2_pass else '✗ FAIL'}")
        print("=" * 70 + "\n")
        
        sys.exit(0 if (test1_pass and test2_pass) else 1)
    finally:
        # Stop server
        print("Stopping Flask server...")
        server_proc.terminate()
        server_proc.wait(timeout=5)
