#!/usr/bin/env python3
"""
Test if the simulation matches the real allocation at 10:00:00 target time.
"""

import requests
import json

target_time = "10:00:00"
base_url = "http://localhost:5001"

# Test with UTA50 race
data = {
    "gpx_filename": "UTMB-UTA50-2026.gpx",
    "is_known_race": True,
    "checkpoint_distances": [],
    "checkpoint_dropbags": [],
    "segment_terrain_types": [],
    "avg_cp_time": 5,
    "z2_pace": 6.5,
    "carbs_per_hour": 60,
    "water_per_hour": 500,
    "climbing_ability": "moderate",
    "skill_level": 0.5,
    "fitness_level": "recreational",
    "include_fatigue": True,
    "pacing_mode": "target_time",
    "target_time": target_time
}

response = requests.post(f"{base_url}/api/calculate", json=data)
result = response.json()

print(f"Target time: {target_time}")
print(f"Thresholds: {result.get('effort_thresholds')}")
print(f"\nSegments:")
for seg in result.get('segments', []):
    print(f"  Effort: {seg.get('effort_level')}")
    print(f"  Time: {seg.get('segment_time_minutes')} min")
    print(f"  Natural pace: {seg.get('natural_pace', 'N/A')}")
    print(f"  Required pace: {seg.get('final_pace', 'N/A')}")
