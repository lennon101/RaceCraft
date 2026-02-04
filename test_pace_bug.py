#!/usr/bin/env python3
"""
Test script to reproduce the pace bug where 4:59 vs 5:00 causes huge time differences.
"""

# Simulate what happens when user enters different pace values
def test_pace_conversion():
    """Test pace conversion from MM:SS to decimal and back."""
    
    # Test case 1: 4:59
    z2_pace_min_1 = 4
    z2_pace_sec_1 = 59
    z2_pace_1 = z2_pace_min_1 + z2_pace_sec_1 / 60.0
    print(f"Test 1: {z2_pace_min_1}:{z2_pace_sec_1:02d} → {z2_pace_1:.10f} min/km")
    
    # Test case 2: 5:00
    z2_pace_min_2 = 5
    z2_pace_sec_2 = 0
    z2_pace_2 = z2_pace_min_2 + z2_pace_sec_2 / 60.0
    print(f"Test 2: {z2_pace_min_2}:{z2_pace_sec_2:02d} → {z2_pace_2:.10f} min/km")
    
    print(f"\nDifference: {z2_pace_2 - z2_pace_1:.10f} min/km")
    
    # Calculate speed for both
    speed_1 = 60.0 / z2_pace_1
    speed_2 = 60.0 / z2_pace_2
    print(f"\nSpeed 1: {speed_1:.10f} km/h")
    print(f"Speed 2: {speed_2:.10f} km/h")
    print(f"Speed difference: {speed_2 - speed_1:.10f} km/h")
    
    # For a 100km race, what's the time difference?
    distance_km = 100
    time_1 = distance_km * z2_pace_1
    time_2 = distance_km * z2_pace_2
    print(f"\nFor {distance_km}km:")
    print(f"Time 1 (4:59): {time_1:.2f} minutes = {time_1/60:.2f} hours")
    print(f"Time 2 (5:00): {time_2:.2f} minutes = {time_2/60:.2f} hours")
    print(f"Time difference: {time_2 - time_1:.2f} minutes = {(time_2 - time_1)/60:.2f} hours")

def test_roundtrip_conversion():
    """Test if pace survives round-trip conversion."""
    import math
    
    test_cases = [
        (4, 59),
        (5, 0),
        (5, 1),
        (6, 30),
    ]
    
    print("\n\nRound-trip conversion test:")
    print("=" * 70)
    
    for min_val, sec_val in test_cases:
        # Original
        original = f"{min_val}:{sec_val:02d}"
        
        # Convert to decimal
        decimal = min_val + sec_val / 60.0
        
        # Convert back
        back_min = math.floor(decimal)
        back_sec = round((decimal % 1) * 60)
        back = f"{back_min}:{back_sec:02d}"
        
        # Check for 60 seconds issue
        if back_sec >= 60:
            print(f"❌ {original} → {decimal:.10f} → {back_min}:{back_sec:02d} (OVERFLOW!)")
        elif original == back:
            print(f"✓ {original} → {decimal:.10f} → {back}")
        else:
            print(f"❌ {original} → {decimal:.10f} → {back} (MISMATCH!)")

def test_floating_point_precision():
    """Test floating point precision issues around 5.0."""
    import math
    
    print("\n\nFloating point precision test:")
    print("=" * 70)
    
    # Test values near 5.0
    test_values = [
        4.9,
        4.95,
        4.983333,
        4.99,
        4.999,
        5.0,
        5.001,
        5.01,
        5.016667,
    ]
    
    for val in test_values:
        min_part = math.floor(val)
        sec_part = round((val % 1) * 60)
        
        # Check if seconds overflow
        if sec_part >= 60:
            print(f"❌ {val:.6f} → {min_part}:{sec_part:02d} (OVERFLOW!)")
        else:
            # Reconstruct
            reconstructed = min_part + sec_part / 60.0
            error = abs(reconstructed - val)
            
            if error > 0.01:  # More than 0.6 seconds error
                print(f"⚠️  {val:.6f} → {min_part}:{sec_part:02d} → {reconstructed:.6f} (error: {error:.6f})")
            else:
                print(f"   {val:.6f} → {min_part}:{sec_part:02d} → {reconstructed:.6f}")

if __name__ == '__main__':
    test_pace_conversion()
    test_roundtrip_conversion()
    test_floating_point_precision()
