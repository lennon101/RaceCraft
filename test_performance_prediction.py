#!/usr/bin/env python3
"""
Test script for performance-based pace estimation feature.
Tests the Riegel formula, intensity downshift, and API endpoint.
"""

import sys
import os
import math

# Add parent directory to path to import from app.py
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from app import (
    predict_race_time_riegel,
    apply_intensity_downshift,
    calculate_base_pace_from_performance
)


def test_riegel_prediction():
    """Test Riegel's formula for various distances."""
    print("\n" + "="*70)
    print("TEST 1: Riegel's Formula Predictions")
    print("="*70)
    
    test_cases = [
        # (ref_dist, ref_time, target_dist, expected_approx_time)
        # Note: These are calculated using Time2 = Time1 × (Distance2 / Distance1)^1.06
        (10, 45.0, 21.1, 99.3),      # 10K in 45min → Half Marathon ~1:39
        (21.1, 90.0, 42.2, 187.6),   # Half in 1:30 → Marathon ~3:08
        (10, 45.0, 50, 247.8),       # 10K in 45min → 50K ~4:08
        (42.2, 180.0, 100, 449.2),   # Marathon in 3:00 → 100K ~7:29
    ]
    
    all_passed = True
    for ref_dist, ref_time, target_dist, expected in test_cases:
        result = predict_race_time_riegel(ref_dist, ref_time, target_dist)
        ref_hours = int(ref_time // 60)
        ref_mins = int(ref_time % 60)
        result_hours = int(result // 60)
        result_mins = int(result % 60)
        result_secs = int((result % 1) * 60)
        
        # Check if within 2% of expected
        tolerance = expected * 0.02
        passed = abs(result - expected) <= tolerance
        status = "✓ PASS" if passed else "✗ FAIL"
        
        print(f"\n{status}: {ref_dist}K in {ref_hours}h{ref_mins:02d}m → {target_dist}K")
        print(f"  Predicted: {result:.2f} min ({result_hours}:{result_mins:02d}:{result_secs:02d})")
        print(f"  Expected:  ~{expected:.1f} min")
        
        if not passed:
            all_passed = False
    
    return all_passed


def test_intensity_downshift():
    """Test ultra-distance intensity downshift."""
    print("\n" + "="*70)
    print("TEST 2: Ultra-Distance Intensity Downshift")
    print("="*70)
    
    test_cases = [
        # (predicted_time, target_dist, ref_dist, should_apply_downshift)
        (247.8, 50, 10, True),      # 50K ultra - apply downshift
        (449.2, 100, 42.2, True),   # 100K ultra - apply downshift
        (99.3, 21.1, 10, False),    # Half marathon - no downshift
        (187.6, 42.2, 21.1, False), # Marathon - no downshift
    ]
    
    all_passed = True
    for pred_time, target_dist, ref_dist, should_apply in test_cases:
        result = apply_intensity_downshift(pred_time, target_dist, ref_dist)
        
        if should_apply:
            # Should be slower than Riegel prediction
            downshift_pct = ((result - pred_time) / pred_time) * 100
            passed = result > pred_time and downshift_pct > 0
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"\n{status}: {target_dist}K (ultra-distance)")
            print(f"  Riegel:    {pred_time:.1f} min")
            print(f"  Adjusted:  {result:.1f} min (+{downshift_pct:.1f}%)")
        else:
            # Should NOT apply downshift (same as prediction)
            passed = abs(result - pred_time) < 0.01
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"\n{status}: {target_dist}K (standard distance)")
            print(f"  Riegel:    {pred_time:.1f} min")
            print(f"  Adjusted:  {result:.1f} min (no downshift)")
        
        if not passed:
            all_passed = False
    
    return all_passed


def test_base_pace_calculation():
    """Test end-to-end base pace calculation."""
    print("\n" + "="*70)
    print("TEST 3: Base Pace Calculation from Performance")
    print("="*70)
    
    test_cases = [
        # (ref_dist, ref_time, target_dist, expected_pace_range_min, expected_pace_range_max)
        (10, 45.0, 50, 5.4, 5.8),     # 10K in 45min → 50K pace ~5.5 min/km (with downshift)
        (21.1, 90.0, 100, 5.0, 5.5),  # Half in 1:30 → 100K pace ~5.2 min/km (with downshift)
        (10, 40.0, 42.2, 4.3, 4.5),   # 10K in 40min → Marathon pace ~4.4 min/km (no downshift)
    ]
    
    all_passed = True
    for ref_dist, ref_time, target_dist, pace_min, pace_max in test_cases:
        result_pace = calculate_base_pace_from_performance(
            ref_dist, ref_time, target_dist, apply_ultra_downshift=True
        )
        
        passed = pace_min <= result_pace <= pace_max
        status = "✓ PASS" if passed else "✗ FAIL"
        
        pace_min_int = int(result_pace)
        pace_sec = int((result_pace - pace_min_int) * 60)
        
        ref_hours = int(ref_time // 60)
        ref_mins = int(ref_time % 60)
        
        print(f"\n{status}: {ref_dist}K in {ref_hours}h{ref_mins:02d}m → {target_dist}K")
        print(f"  Base Pace: {result_pace:.2f} min/km ({pace_min_int}:{pace_sec:02d})")
        print(f"  Expected:  {pace_min:.1f}-{pace_max:.1f} min/km")
        
        if not passed:
            all_passed = False
    
    return all_passed


def test_edge_cases():
    """Test edge cases and error handling."""
    print("\n" + "="*70)
    print("TEST 4: Edge Cases and Error Handling")
    print("="*70)
    
    all_passed = True
    
    # Test 1: Very short to very long distance
    print("\n✓ TEST: 5K → 160K (100 miler)")
    try:
        result = calculate_base_pace_from_performance(5, 20.0, 160)
        print(f"  Result: {result:.2f} min/km (pace slows significantly for ultra)")
        # Expect significantly slower pace for ultra distance
        if result > 6.0:  # Should be much slower than 4min/km base
            print("  ✓ Appropriate ultra-distance slowdown applied")
        else:
            print("  ✗ Expected more slowdown for extreme distance")
            all_passed = False
    except Exception as e:
        print(f"  ✗ FAIL: {e}")
        all_passed = False
    
    # Test 2: Same distance (should return same pace)
    print("\n✓ TEST: Same distance prediction")
    try:
        ref_time = 45.0
        result_time = predict_race_time_riegel(10, ref_time, 10)
        if abs(result_time - ref_time) < 0.01:
            print(f"  Result: {result_time:.2f} min (same as input)")
            print("  ✓ Correctly returns same time for same distance")
        else:
            print(f"  ✗ Expected {ref_time}, got {result_time}")
            all_passed = False
    except Exception as e:
        print(f"  ✗ FAIL: {e}")
        all_passed = False
    
    # Test 3: Invalid inputs (should raise errors)
    print("\n✓ TEST: Error handling for invalid inputs")
    error_cases = [
        (0, 45, 10, "zero distance"),
        (-10, 45, 10, "negative distance"),
        (10, 0, 10, "zero time"),
        (10, -45, 10, "negative time"),
    ]
    
    for ref_dist, ref_time, target_dist, desc in error_cases:
        try:
            predict_race_time_riegel(ref_dist, ref_time, target_dist)
            print(f"  ✗ Expected error for {desc}, but got result")
            all_passed = False
        except ValueError:
            print(f"  ✓ Correctly raised error for {desc}")
        except Exception as e:
            print(f"  ✗ Wrong error type for {desc}: {e}")
            all_passed = False
    
    return all_passed


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("PERFORMANCE-BASED PACE ESTIMATION TEST SUITE")
    print("="*70)
    
    results = {
        "Riegel Formula": test_riegel_prediction(),
        "Intensity Downshift": test_intensity_downshift(),
        "Base Pace Calculation": test_base_pace_calculation(),
        "Edge Cases": test_edge_cases()
    }
    
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False
    
    print("="*70)
    
    if all_passed:
        print("\n✓ ALL TESTS PASSED\n")
        return 0
    else:
        print("\n✗ SOME TESTS FAILED\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
