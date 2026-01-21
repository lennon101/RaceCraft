import xml.etree.ElementTree as ET
import math
import os
import csv
from pathlib import Path

# Configuration
GPX_FILENAME = "route.gpx"  # Name of the GPX file in the same directory
ELEVATION_GAIN_FACTOR = 6.0  # Seconds added per meter of elevation gain (Naismith's rule: ~10 sec/m)
FATIGUE_MULTIPLIER = 2  # Percentage pace slowdown per hour of running (0.5 = 0.5% slower per hour)
MAX_DOWNHILL_SPEED_INCREASE = 20.0  # Maximum percentage pace can increase on downhills (20 = max 20% faster)
DEFAULT_CARBS_PER_HOUR = 60.0  # Default target carbs per hour in grams
DEFAULT_WATER_PER_HOUR = 500.0  # Default target water per hour in mL

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees).
    Returns distance in kilometers.
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371  # Radius of earth in kilometers
    return c * r

def parse_gpx_file(gpx_path):
    """
    Parse GPX file and extract trackpoints with coordinates and elevation.
    Returns list of trackpoints [(lat, lon, elev), ...]
    """
    tree = ET.parse(gpx_path)
    root = tree.getroot()
    
    # Extract namespace from root tag if present
    namespace_dict = {}
    if root.tag.startswith('{'):
        ns = root.tag.split('}')[0].strip('{')
        namespace_dict = {'ns': ns}
    
    trackpoints = []
    
    # Try multiple ways to find trackpoints/routepoints to handle different GPX formats
    trkpt_list = []
    
    if namespace_dict:
        # Try with namespace - first tracks, then routes
        trkpt_list = root.findall('.//{%s}trkpt' % namespace_dict['ns'])
        if not trkpt_list:
            trkpt_list = root.findall('.//{%s}rtept' % namespace_dict['ns'])
    
    if not trkpt_list:
        # Try without namespace - first tracks, then routes
        trkpt_list = root.findall('.//trkpt')
        if not trkpt_list:
            trkpt_list = root.findall('.//rtept')
    
    if not trkpt_list:
        print(f"DEBUG: Root tag: {root.tag}")
        print(f"DEBUG: No trackpoints found. Trying alternative search methods...")
        # Try even more flexible search
        for elem in root.iter():
            if elem.tag.endswith('trkpt') or elem.tag.endswith('rtept'):
                trkpt_list.append(elem)
    
    print(f"Found {len(trkpt_list)} trackpoints")
    
    for trkpt in trkpt_list:
        lat = float(trkpt.get('lat'))
        lon = float(trkpt.get('lon'))
        
        # Get elevation - try multiple approaches
        ele_elem = None
        if namespace_dict:
            ele_elem = trkpt.find('{%s}ele' % namespace_dict['ns'])
        if ele_elem is None:
            ele_elem = trkpt.find('ele')
        
        elev = float(ele_elem.text) if ele_elem is not None and ele_elem.text else 0.0
        
        trackpoints.append((lat, lon, elev))
    
    return trackpoints

def calculate_total_distance(trackpoints):
    """
    Calculate total distance of the route in kilometers.
    """
    total_distance = 0.0
    for i in range(len(trackpoints) - 1):
        lat1, lon1, _ = trackpoints[i]
        lat2, lon2, _ = trackpoints[i + 1]
        total_distance += haversine_distance(lat1, lon1, lat2, lon2)
    
    return total_distance

def find_checkpoint_indices(trackpoints, checkpoint_distances):
    """
    Find the trackpoint indices closest to each checkpoint distance marker.
    """
    cumulative_dist = 0.0
    distances = [0.0]  # Start at 0
    
    for i in range(len(trackpoints) - 1):
        lat1, lon1, _ = trackpoints[i]
        lat2, lon2, _ = trackpoints[i + 1]
        cumulative_dist += haversine_distance(lat1, lon1, lat2, lon2)
        distances.append(cumulative_dist)
    
    checkpoint_indices = [0]  # Start point
    
    for cp_dist in checkpoint_distances:
        # Find the closest trackpoint to this checkpoint distance
        closest_idx = min(range(len(distances)), 
                         key=lambda i: abs(distances[i] - cp_dist))
        checkpoint_indices.append(closest_idx)
    
    checkpoint_indices.append(len(trackpoints) - 1)  # Finish point
    
    return checkpoint_indices, distances

def calculate_elevation_change(trackpoints, start_idx, end_idx):
    """
    Calculate total elevation gain and loss between two trackpoint indices.
    """
    gain = 0.0
    loss = 0.0
    
    for i in range(start_idx, end_idx):
        elev_change = trackpoints[i + 1][2] - trackpoints[i][2]
        if elev_change > 0:
            gain += elev_change
        else:
            loss += abs(elev_change)
    
    return gain, loss

def adjust_pace_for_elevation(base_pace_min_per_km, elevation_gain, elevation_loss, distance_km, cumulative_time_hours=0.0, elev_gain_factor=ELEVATION_GAIN_FACTOR):
    """
    Adjust pace based on elevation changes using elevation gain factor and fatigue.
    Base pace is in minutes per kilometer on flat ground (Z2 pace).
    Fatigue is applied based on cumulative time spent running.
    Returns: (final_pace, elevation_adjusted_pace, fatigue_seconds_per_km)
    """
    if distance_km == 0:
        return base_pace_min_per_km, base_pace_min_per_km, 0.0
    
    # Calculate time added by elevation using elevation gain factor (seconds per meter)
    # Gain adds time, loss subtracts time (at ~30% of gain factor)
    elev_time_seconds = (elevation_gain * elev_gain_factor) - (elevation_loss * elev_gain_factor * 0.3)
    elev_time_minutes = elev_time_seconds / 60.0
    
    # Calculate elevation-adjusted pace (without fatigue first)
    segment_time_no_fatigue = (distance_km * base_pace_min_per_km) + elev_time_minutes
    pace_with_elev_only = segment_time_no_fatigue / distance_km if distance_km > 0 else base_pace_min_per_km
    
    # Apply downhill speed limit BEFORE fatigue (relative to base pace)
    # Minimum pace (fastest): can't be more than MAX_DOWNHILL_SPEED_INCREASE% faster than base
    min_allowed_pace = base_pace_min_per_km * (1.0 - MAX_DOWNHILL_SPEED_INCREASE / 100.0)
    pace_with_elev_limited = max(pace_with_elev_only, min_allowed_pace)
    
    # Now apply fatigue factor
    fatigue_factor = 1.0 + (cumulative_time_hours * FATIGUE_MULTIPLIER / 100.0)
    fatigued_pace = pace_with_elev_limited * fatigue_factor
    
    # Calculate fatigue impact in seconds per km
    fatigue_seconds_per_km = (fatigued_pace - pace_with_elev_limited) * 60.0
    
    # Apply maximum pace limit (can't be more than 2x slower than base)
    max_allowed_pace = base_pace_min_per_km * 2.0
    final_pace = min(fatigued_pace, max_allowed_pace)
    
    return final_pace, pace_with_elev_limited, fatigue_seconds_per_km

def format_time(minutes):
    """
    Format minutes into HH:MM:SS format.
    """
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    secs = int((minutes % 1) * 60)
    return f"{hours:02d}:{mins:02d}:{secs:02d}"

def export_to_csv(segments, total_moving_time, total_cp_time, total_distance, num_checkpoints, race_start_time, gpx_filename):
    """
    Export race plan to CSV file for Excel.
    """
    # Generate filename based on GPX file
    csv_filename = gpx_filename.replace('.gpx', '_race_plan.csv')
    
    try:
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header row
            header = ['Segment', 'Distance (km)', 'Elev Gain (m)', 'Elev Loss (m)', 'Net Elev (m)', 
                     'Elev Pace (min/km)', 'Fatigue (mm:ss)', 'Final Pace (min/km)', 
                     'Segment Time', 'Carbs (g)', 'Water (L)', 'Cumulative Time']
            if race_start_time:
                header.append('Time of Day')
            writer.writerow(header)
            
            # Write data rows
            for seg in segments:
                from_to = f"{seg['from']} → {seg['to']}"
                elev_pace_str = f"{int(seg['elev_pace'])}:{int((seg['elev_pace'] % 1) * 60):02d}"
                pace_str = f"{int(seg['pace'])}:{int((seg['pace'] % 1) * 60):02d}"
                fatigue_mins = int(seg['fatigue_seconds'] // 60)
                fatigue_secs = int(seg['fatigue_seconds'] % 60)
                fatigue_str = f"+{fatigue_mins}:{fatigue_secs:02d}"
                
                row = [
                    from_to,
                    f"{seg['distance']:.2f}",
                    f"{seg['elev_gain']:.0f}",
                    f"{seg['elev_loss']:.0f}",
                    f"{seg['net_elev']:+.0f}",
                    elev_pace_str,
                    fatigue_str,
                    pace_str,
                    format_time(seg['segment_time']),
                    f"{seg['target_carbs']:.0f}",
                    f"{seg['target_water']:.1f}",
                    format_time(seg['cumulative_time'])
                ]
                if race_start_time:
                    row.append(seg['time_of_day'])
                writer.writerow(row)
            
            # Write summary section
            writer.writerow([])  # Blank row
            writer.writerow(['SUMMARY'])
            writer.writerow(['Total Moving Time', format_time(total_moving_time)])
            writer.writerow(['Total CP Time', format_time(total_cp_time)])
            writer.writerow(['Total Race Time', format_time(segments[-1]['cumulative_time'])])
            writer.writerow(['Total Distance (km)', f"{total_distance:.2f}"])
            writer.writerow(['Total Elev Gain (m)', f"{sum(s['elev_gain'] for s in segments):.0f}"])
            writer.writerow(['Total Carbs (g)', f"{sum(s['target_carbs'] for s in segments):.0f}"])
            writer.writerow(['Total Water (L)', f"{sum(s['target_water'] for s in segments):.1f}"])
        
        print(f"\n✓ Race plan exported to: {csv_filename}")
        return True
    except Exception as e:
        print(f"\n✗ Error exporting to CSV: {e}")
        return False

def main():
    print("=" * 70)
    print("RACE FUEL & PACING PLANNER")
    print("=" * 70)
    print()
    
    # Find all GPX files in the directory
    script_dir = Path(__file__).parent
    gpx_files = list(script_dir.glob("*.gpx"))
    
    if not gpx_files:
        print(f"ERROR: No GPX files found in {script_dir}")
        return
    
    # Display available GPX files
    print("Available GPX files:")
    for i, gpx_file in enumerate(gpx_files, 1):
        print(f"  {i}. {gpx_file.name}")
    print()
    
    # Prompt user to select a file
    while True:
        try:
            selection = input(f"Select a GPX file (1-{len(gpx_files)}): ").strip()
            file_index = int(selection) - 1
            
            if 0 <= file_index < len(gpx_files):
                gpx_path = gpx_files[file_index]
                break
            else:
                print(f"  ERROR: Please enter a number between 1 and {len(gpx_files)}")
        except ValueError:
            print("  ERROR: Please enter a valid number")
    
    print(f"\nUsing GPX file: {gpx_path.name}")
    print()
    
    # Parse GPX file
    print("Parsing GPX file...")
    trackpoints = parse_gpx_file(gpx_path)
    total_distance = calculate_total_distance(trackpoints)
    
    print(f"Total route distance: {total_distance:.2f} km ({total_distance * 0.621371:.2f} miles)")
    print()
    
    # Option to calculate elevation gain factor from previous race
    elevation_factor = ELEVATION_GAIN_FACTOR  # Start with default
    calc_elev_factor = input("Do you want to calculate elevation gain factor from a previous race? (y/n): ").strip().lower()
    
    if calc_elev_factor in ['y', 'yes']:
        print("\nEnter details from your previous race:")
        prev_distance = float(input("  Race distance (km): "))
        prev_elevation = float(input("  Total elevation gain (m): "))
        
        print("  Moving time (format: HH:MM:SS or just minutes): ", end="")
        prev_time_input = input().strip()
        
        # Parse time input
        if ':' in prev_time_input:
            time_parts = prev_time_input.split(':')
            if len(time_parts) == 3:  # HH:MM:SS
                prev_time_minutes = int(time_parts[0]) * 60 + int(time_parts[1]) + int(time_parts[2]) / 60.0
            elif len(time_parts) == 2:  # MM:SS
                prev_time_minutes = int(time_parts[0]) + int(time_parts[1]) / 60.0
            else:
                prev_time_minutes = float(prev_time_input)
        else:
            prev_time_minutes = float(prev_time_input)
        
        print("  Your estimated flat pace for that distance (format: MM:SS per km): ", end="")
        flat_pace_input = input().strip()
        flat_pace_parts = flat_pace_input.split(':')
        flat_pace_min_per_km = float(flat_pace_parts[0]) + float(flat_pace_parts[1]) / 60.0
        
        # Calculate elevation gain factor
        expected_flat_time = prev_distance * flat_pace_min_per_km
        extra_time_minutes = prev_time_minutes - expected_flat_time
        extra_time_seconds = extra_time_minutes * 60.0
        
        if prev_elevation > 0:
            elevation_factor = extra_time_seconds / prev_elevation
            print(f"\n  Calculated Elevation Gain Factor: {elevation_factor:.2f} seconds per meter")
        else:
            print("\n  ERROR: Elevation gain must be greater than 0. Using default factor.")
            print(f"  Using default factor: {elevation_factor:.2f} seconds per meter")
        print()
    else:
        print(f"Using default elevation gain factor: {elevation_factor:.2f} seconds per meter")
        print()
    
    # Get user inputs
    num_checkpoints = int(input("Number of checkpoints (not including start/finish): "))
    avg_cp_time = float(input("Average expected time at each checkpoint (minutes): "))
    
    checkpoint_distances = []
    print("\nEnter the distance marker for each checkpoint:")
    for i in range(num_checkpoints):
        while True:
            try:
                dist = float(input(f"  Checkpoint {i + 1} distance (km): "))
                
                # Validate: must be greater than previous checkpoint (if any)
                if checkpoint_distances and dist <= checkpoint_distances[-1]:
                    print(f"    ERROR: Distance must be greater than previous checkpoint ({checkpoint_distances[-1]:.2f} km)")
                    continue
                
                # Validate: must not exceed total distance
                if dist > total_distance:
                    print(f"    ERROR: Distance cannot exceed total route distance ({total_distance:.2f} km)")
                    continue
                
                # Valid input
                checkpoint_distances.append(dist)
                break
            except ValueError:
                print("    ERROR: Please enter a valid number")
                continue
    
    # Get Z2 pace
    print("\nEnter your Zone 2 pace on flat ground:")
    while True:
        try:
            z2_pace_input = input("  (format: MM:SS per km, e.g., 6:30): ").strip()
            
            if ':' not in z2_pace_input:
                print("    ERROR: Please use MM:SS format (e.g., 6:30)")
                continue
            
            pace_parts = z2_pace_input.split(':')
            
            if len(pace_parts) != 2:
                print("    ERROR: Please use MM:SS format (e.g., 6:30)")
                continue
            
            minutes = float(pace_parts[0])
            seconds = float(pace_parts[1])
            
            if minutes < 0 or seconds < 0 or seconds >= 60:
                print("    ERROR: Invalid time values. Seconds must be between 0-59")
                continue
            
            z2_pace_min_per_km = minutes + seconds / 60.0
            break
        except ValueError:
            print("    ERROR: Please enter valid numbers in MM:SS format (e.g., 6:30)")
            continue
    
    # Get race start time (optional)
    print("\nEnter race start time (optional, press Enter to skip):")
    race_start_time = None
    while True:
        start_time_input = input("  (format: HH:MM, e.g., 06:00): ").strip()
        
        if not start_time_input:
            # User pressed Enter - no start time
            break
        
        try:
            if ':' not in start_time_input:
                print("    ERROR: Please use HH:MM format (e.g., 06:00)")
                continue
            
            time_parts = start_time_input.split(':')
            
            if len(time_parts) != 2:
                print("    ERROR: Please use HH:MM format (e.g., 06:00)")
                continue
            
            hours = int(time_parts[0])
            minutes = int(time_parts[1])
            
            if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
                print("    ERROR: Invalid time. Hours must be 0-23, minutes 0-59")
                continue
            
            race_start_time = (hours, minutes)
            break
        except ValueError:
            print("    ERROR: Please enter valid numbers in HH:MM format (e.g., 06:00)")
            continue
    
    # Get carb target
    carbs_input = input(f"\nTarget carbs per hour in grams (default: {DEFAULT_CARBS_PER_HOUR:.0f}g, press Enter to use default): ").strip()
    carbs_per_hour = float(carbs_input) if carbs_input else DEFAULT_CARBS_PER_HOUR
    
    # Get water target
    water_input = input(f"Target water per hour in mL (default: {DEFAULT_WATER_PER_HOUR:.0f}mL, press Enter to use default): ").strip()
    water_per_hour = float(water_input) if water_input else DEFAULT_WATER_PER_HOUR
    
    print("\n" + "=" * 70)
    print("CALCULATING RACE PLAN...")
    print("=" * 70)
    print()
    
    # Find checkpoint indices in trackpoints
    checkpoint_indices, distances = find_checkpoint_indices(trackpoints, checkpoint_distances)
    
    # Calculate segment data
    segments = []
    cumulative_time = 0.0
    total_moving_time = 0.0
    
    segment_labels = ["Start"]
    for i in range(num_checkpoints):
        segment_labels.append(f"CP{i + 1}")
    segment_labels.append("Finish")
    
    for i in range(len(checkpoint_indices) - 1):
        start_idx = checkpoint_indices[i]
        end_idx = checkpoint_indices[i + 1]
        
        # Calculate segment distance
        segment_dist = distances[end_idx] - distances[start_idx]
        
        # Calculate elevation changes
        elev_gain, elev_loss = calculate_elevation_change(trackpoints, start_idx, end_idx)
        net_elev_change = elev_gain - elev_loss
        
        # Calculate cumulative time in hours for fatigue calculation
        cumulative_hours = total_moving_time / 60.0
        
        # Adjust pace for elevation and fatigue
        adjusted_pace, elev_adjusted_pace, fatigue_seconds = adjust_pace_for_elevation(z2_pace_min_per_km, elev_gain, elev_loss, segment_dist, cumulative_hours, elevation_factor)
        
        # Calculate segment time
        segment_time = segment_dist * adjusted_pace
        
        # Track moving time (without checkpoint stops)
        total_moving_time += segment_time
        
        # Add checkpoint time (except for the first segment)
        if i > 0:
            cumulative_time += avg_cp_time
        
        cumulative_time += segment_time
        
        # Calculate target carbs for segment (rounded to nearest 10)
        segment_hours = segment_time / 60.0
        target_carbs = round((segment_hours * carbs_per_hour) / 10) * 10
        
        # Calculate target water for segment in liters (rounded to nearest 0.1L)
        target_water_L = round((segment_hours * water_per_hour / 1000) * 10) / 10
        
        # Calculate time of day if start time was provided
        time_of_day = None
        if race_start_time:
            total_minutes = cumulative_time
            start_hours, start_minutes = race_start_time
            start_total_minutes = start_hours * 60 + start_minutes
            current_total_minutes = start_total_minutes + total_minutes
            
            # Handle day overflow
            current_hours = int(current_total_minutes // 60) % 24
            current_mins = int(current_total_minutes % 60)
            time_of_day = f"{current_hours:02d}:{current_mins:02d}"
        
        segments.append({
            'from': segment_labels[i],
            'to': segment_labels[i + 1],
            'distance': segment_dist,
            'elev_gain': elev_gain,
            'elev_loss': elev_loss,
            'net_elev': net_elev_change,
            'elev_pace': elev_adjusted_pace,
            'pace': adjusted_pace,
            'fatigue_seconds': fatigue_seconds,
            'segment_time': segment_time,
            'cumulative_time': cumulative_time,
            'target_carbs': target_carbs,
            'target_water': target_water_L,
            'time_of_day': time_of_day
        })
    
    # Display results table
    if race_start_time:
        print(f"{'Segment':<20} {'Dist(km)':<10} {'Elev+/-(m)':<15} {'Net(m)':<10} {'Elev Pace':<11} {'Fatigue':<10} {'Final Pace':<11} {'Time':<10} {'Carbs(g)':<10} {'Water(L)':<10} {'Cumul Time':<12} {'Time of Day':<12}")
        print("-" * 159)
    else:
        print(f"{'Segment':<20} {'Dist(km)':<10} {'Elev+/-(m)':<15} {'Net(m)':<10} {'Elev Pace':<11} {'Fatigue':<10} {'Final Pace':<11} {'Time':<10} {'Carbs(g)':<10} {'Water(L)':<10} {'Cumul Time':<12}")
        print("-" * 147)
    
    for seg in segments:
        from_to = f"{seg['from']} → {seg['to']}"
        elev_change = f"+{seg['elev_gain']:.0f}/-{seg['elev_loss']:.0f}"
        net_elev_str = f"{seg['net_elev']:+.0f}"
        elev_pace_str = f"{int(seg['elev_pace'])}:{int((seg['elev_pace'] % 1) * 60):02d}"
        pace_str = f"{int(seg['pace'])}:{int((seg['pace'] % 1) * 60):02d}"
        # Format fatigue as mm:ss
        fatigue_mins = int(seg['fatigue_seconds'] // 60)
        fatigue_secs = int(seg['fatigue_seconds'] % 60)
        fatigue_str = f"+{fatigue_mins}:{fatigue_secs:02d}"
        seg_time_str = format_time(seg['segment_time'])
        carbs_str = f"{seg['target_carbs']:.0f}"
        water_str = f"{seg['target_water']:.1f}"
        cumul_time_str = format_time(seg['cumulative_time'])
        
        if race_start_time:
            time_of_day_str = seg['time_of_day']
            print(f"{from_to:<20} {seg['distance']:>8.2f}  {elev_change:<15} {net_elev_str:<10} {elev_pace_str:<11} {fatigue_str:<10} {pace_str:<11} {seg_time_str:<10} {carbs_str:<10} {water_str:<10} {cumul_time_str:<12} {time_of_day_str:<12}")
        else:
            print(f"{from_to:<20} {seg['distance']:>8.2f}  {elev_change:<15} {net_elev_str:<10} {elev_pace_str:<11} {fatigue_str:<10} {pace_str:<11} {seg_time_str:<10} {carbs_str:<10} {water_str:<10} {cumul_time_str:<12}")
    
    if race_start_time:
        print("-" * 159)
    else:
        print("-" * 147)
    print(f"\n{'TOTAL MOVING TIME:':<20} {format_time(total_moving_time)}")
    print(f"{'TOTAL CP TIME:':<20} {format_time(avg_cp_time * num_checkpoints)}")
    print(f"{'TOTAL RACE TIME:':<20} {format_time(cumulative_time)}")
    print(f"\n{'TOTAL DISTANCE:':<20} {total_distance:.2f} km")
    print(f"{'TOTAL ELEV GAIN:':<20} {sum(s['elev_gain'] for s in segments):.0f} m")
    print(f"{'TOTAL CARBS:':<20} {sum(s['target_carbs'] for s in segments):.0f} g")
    print(f"{'TOTAL WATER:':<20} {sum(s['target_water'] for s in segments):.1f} L")
    print()    
    # Prompt for export
    export_choice = input("Would you like to export this race plan to an Excel spreadsheet (CSV)? (y/n): ").strip().lower()
    if export_choice in ['y', 'yes']:
        export_to_csv(segments, total_moving_time, avg_cp_time * num_checkpoints, total_distance, num_checkpoints, race_start_time, gpx_path.name)
if __name__ == "__main__":
    main()
