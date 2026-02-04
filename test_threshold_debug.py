#!/usr/bin/env python3
"""
Debug script to test threshold calculation accuracy.
Tests multiple target times and shows which segments get which effort labels.
"""

import json
import requests

# Test with UTA50 race
gpx_filename = "data/known_races/UTMB-UTA50-2026.gpx"
checkpoint_distances = []  # No checkpoints to match UI test

# Test different target times around the protect threshold
target_times = [
    "09:30:00",  # Well before protect threshold
    "09:45:00",  # Just before threshold
    "09:46:00",  # At threshold
    "09:46:30",  # Just after threshold
    "09:47:00",  # After threshold
    "10:00:00",  # Well after threshold
]

base_url = "http://localhost:5001"

for target_time in target_times:
    print(f"\n{'='*80}")
    print(f"Testing target time: {target_time}")
    print('='*80)
    
    # Prepare request data
    data = {
        "gpx_filename": "UTMB-UTA50-2026.gpx",
        "is_known_race": True,
        "checkpoint_distances": checkpoint_distances,
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
    
    try:
        # Make API request
        response = requests.post(f"{base_url}/api/calculate", json=data)
        result = response.json()
        
        if 'error' in result:
            print(f"ERROR: {result['error']}")
            continue
            
        # Print thresholds
        if 'effort_thresholds' in result:
            thresholds = result['effort_thresholds']
            print(f"\nThresholds:")
            print(f"  Natural: {thresholds['natural_time']}")
            print(f"  Push: {thresholds['push_threshold']}")
            print(f"  Protect: {thresholds['protect_threshold']}")
        
        # Print segment effort labels
        print(f"\nSegments:")
        for i, seg in enumerate(result.get('segments', [])):
            effort = seg.get('effort_level', 'N/A')
            segment_time = seg.get('segment_time_minutes', 0)
            hrs = int(segment_time // 60)
            mins = int(segment_time % 60)
            seg_name = seg.get('name', f"Segment {i+1}")
            print(f"  {seg_name:30s} {hrs:02d}:{mins:02d} - {effort:8s} (pace: {seg.get('final_pace', 'N/A')})")
            
        # Count effort levels
        effort_counts = {}
        for seg in result.get('segments', []):
            effort = seg.get('effort_level', 'N/A')
            effort_counts[effort] = effort_counts.get(effort, 0) + 1
        
        print(f"\nEffort Summary: {effort_counts}")
        
    except Exception as e:
        print(f"ERROR: {e}")
