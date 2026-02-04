#!/usr/bin/env python3
"""
Test to see what happens when seconds=60 is sent to the backend.
"""

# What happens if someone manually sets seconds to 60?
z2_pace_min = 4
z2_pace_sec = 60  # Invalid!

z2_pace = z2_pace_min + z2_pace_sec / 60.0
print(f"If user enters {z2_pace_min}:{z2_pace_sec} → {z2_pace} min/km")
print(f"This equals {z2_pace_min + 1}:00")

# Expected:
expected = 5 + 0 / 60.0
print(f"\nExpected 5:00 → {expected} min/km")
print(f"\nDifference: {z2_pace - expected} min/km")

# For 100km
distance = 100
time_wrong = distance * z2_pace
time_right = distance * expected

print(f"\nFor {distance}km:")
print(f"Wrong (4:60): {time_wrong:.2f} minutes = {time_wrong/60:.2f} hours")
print(f"Right (5:00): {time_right:.2f} minutes = {time_right/60:.2f} hours")
print(f"Time difference: {time_wrong - time_right:.2f} minutes = {(time_wrong - time_right)/60:.2f} hours")
