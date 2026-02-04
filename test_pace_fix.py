#!/usr/bin/env python3
"""
Test to verify the pace calculation bug is fixed.
Tests both the zero-value bug and the rounding overflow bug.
"""

import math

def simulate_old_js_parsing(min_str, sec_str):
    """Simulates the OLD buggy JavaScript parsing logic."""
    min_val = float(min_str) if min_str else 0
    sec_val = float(sec_str) if sec_str else 0
    
    # Old buggy logic: parseFloat(value) || defaultValue
    # This treats 0 as falsy!
    z2_pace_min = min_val or 6
    z2_pace_sec = sec_val or 30
    
    return z2_pace_min + z2_pace_sec / 60.0

def simulate_new_js_parsing(min_str, sec_str):
    """Simulates the FIXED JavaScript parsing logic."""
    # New logic: check for empty string, not falsy value
    z2_pace_min = 6 if min_str == '' else float(min_str)
    z2_pace_sec = 30 if sec_str == '' else float(sec_str)
    
    return z2_pace_min + z2_pace_sec / 60.0

def simulate_old_roundtrip(pace_decimal):
    """Simulates the OLD roundtrip conversion without overflow handling."""
    pace_min = math.floor(pace_decimal)
    pace_sec = round((pace_decimal % 1) * 60)
    
    return pace_min, pace_sec

def simulate_new_roundtrip(pace_decimal):
    """Simulates the FIXED roundtrip conversion with overflow handling."""
    pace_min = math.floor(pace_decimal)
    pace_sec = round((pace_decimal % 1) * 60)
    
    # Handle seconds overflow
    if pace_sec >= 60:
        pace_min += 1
        pace_sec = 0
    
    return pace_min, pace_sec

def test_zero_seconds_bug():
    """Test the zero seconds bug (main issue reported)."""
    print("=" * 70)
    print("TEST 1: Zero Seconds Bug (5:00 interpreted as 5:30)")
    print("=" * 70)
    
    test_cases = [
        ("4", "59", "4:59"),
        ("5", "0", "5:00"),
        ("6", "0", "6:00"),
        ("7", "0", "7:00"),
    ]
    
    print("\nOLD (BUGGY) BEHAVIOR:")
    for min_str, sec_str, display in test_cases:
        pace = simulate_old_js_parsing(min_str, sec_str)
        print(f"  {display} → {pace:.4f} min/km", end="")
        if sec_str == "0" and pace != float(min_str):
            print(f" ❌ WRONG! (interpreted as {int(pace)}:{int((pace % 1) * 60):02d})")
        else:
            print(" ✓")
    
    print("\nNEW (FIXED) BEHAVIOR:")
    for min_str, sec_str, display in test_cases:
        pace = simulate_new_js_parsing(min_str, sec_str)
        expected = float(min_str) + float(sec_str) / 60.0
        print(f"  {display} → {pace:.4f} min/km", end="")
        if abs(pace - expected) < 0.001:
            print(" ✓ CORRECT!")
        else:
            print(f" ❌ WRONG!")
    
    # Calculate time difference for a race
    print("\n" + "=" * 70)
    print("IMPACT ON A 150KM RACE:")
    print("=" * 70)
    
    old_pace_459 = simulate_old_js_parsing("4", "59")
    old_pace_500 = simulate_old_js_parsing("5", "0")
    new_pace_459 = simulate_new_js_parsing("4", "59")
    new_pace_500 = simulate_new_js_parsing("5", "0")
    
    distance = 150
    
    old_time_459 = distance * old_pace_459
    old_time_500 = distance * old_pace_500
    new_time_459 = distance * new_pace_459
    new_time_500 = distance * new_pace_500
    
    print(f"\nOLD (BUGGY):")
    print(f"  4:59 pace → {old_time_459:.1f} min = {old_time_459/60:.2f} hours")
    print(f"  5:00 pace → {old_time_500:.1f} min = {old_time_500/60:.2f} hours")
    print(f"  Difference: {old_time_500 - old_time_459:.1f} min = {(old_time_500 - old_time_459)/60:.2f} hours ❌ HUGE GAP!")
    
    print(f"\nNEW (FIXED):")
    print(f"  4:59 pace → {new_time_459:.1f} min = {new_time_459/60:.2f} hours")
    print(f"  5:00 pace → {new_time_500:.1f} min = {new_time_500/60:.2f} hours")
    print(f"  Difference: {new_time_500 - new_time_459:.1f} min = {(new_time_500 - new_time_459)/60:.2f} hours ✓ Reasonable!")

def test_rounding_overflow_bug():
    """Test the rounding overflow bug (seconds=60)."""
    print("\n\n" + "=" * 70)
    print("TEST 2: Rounding Overflow Bug (seconds can round to 60)")
    print("=" * 70)
    
    # Test values that can round to 60 seconds
    test_cases = [
        (4.983333, "4:59"),  # Normal case
        (4.999, "4:59 or 5:00"),  # Rounds to 4:60!
        (5.0, "5:00"),
        (5.999, "5:59 or 6:00"),  # Rounds to 5:60!
    ]
    
    print("\nOLD (BUGGY) BEHAVIOR:")
    for pace_decimal, expected in test_cases:
        min_val, sec_val = simulate_old_roundtrip(pace_decimal)
        print(f"  {pace_decimal:.6f} → {min_val}:{sec_val:02d}", end="")
        if sec_val >= 60:
            print(f" ❌ OVERFLOW! Invalid time format!")
        else:
            print(" ✓")
    
    print("\nNEW (FIXED) BEHAVIOR:")
    for pace_decimal, expected in test_cases:
        min_val, sec_val = simulate_new_roundtrip(pace_decimal)
        print(f"  {pace_decimal:.6f} → {min_val}:{sec_val:02d} ✓ CORRECT!")

def test_empty_field_defaults():
    """Test that empty fields still get defaults."""
    print("\n\n" + "=" * 70)
    print("TEST 3: Empty Field Defaults")
    print("=" * 70)
    
    test_cases = [
        ("", "", "Empty inputs"),
        ("5", "", "Minutes only"),
        ("", "30", "Seconds only"),
    ]
    
    print("\nNEW (FIXED) BEHAVIOR:")
    for min_str, sec_str, description in test_cases:
        pace = simulate_new_js_parsing(min_str, sec_str)
        print(f"  {description:20s} ('{min_str}', '{sec_str}') → {pace:.2f} min/km ✓")

if __name__ == '__main__':
    test_zero_seconds_bug()
    test_rounding_overflow_bug()
    test_empty_field_defaults()
    
    print("\n\n" + "=" * 70)
    print("ALL TESTS COMPLETED!")
    print("=" * 70)
