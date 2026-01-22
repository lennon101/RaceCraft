from flask import Flask, render_template, request, jsonify, send_file
import xml.etree.ElementTree as ET
import math
import os
import json
import csv
from pathlib import Path
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['SAVED_PLANS_FOLDER'] = 'saved_plans'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['SAVED_PLANS_FOLDER'], exist_ok=True)

# Constants
ELEVATION_GAIN_FACTOR = 6.0
FATIGUE_MULTIPLIER = 2.0
MAX_DOWNHILL_SPEED_INCREASE = 20.0
DEFAULT_CARBS_PER_HOUR = 60.0
DEFAULT_WATER_PER_HOUR = 500.0

# Ability level fatigue multipliers
ABILITY_FATIGUE_MAP = {
    'strong': 1.0,
    'average': 2.0,
    'weak': 3.0
}

# Segment difficulty pace adjustments (in seconds per km)
DIFFICULTY_PACE_MAP = {
    'easy': -10,         # Road/Flat
    'normal': 0,         # Default (no penalty)
    'technical_uphill': 10,   # Technical terrain climbing
    'technical_downhill': 20  # Technical terrain descending
}

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points on earth in kilometers."""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371
    return c * r

def parse_gpx_file(gpx_path):
    """Parse GPX file and extract trackpoints."""
    tree = ET.parse(gpx_path)
    root = tree.getroot()
    
    namespace_dict = {}
    if root.tag.startswith('{'):
        ns = root.tag.split('}')[0].strip('{')
        namespace_dict = {'ns': ns}
    
    trackpoints = []
    trkpt_list = []
    
    if namespace_dict:
        trkpt_list = root.findall('.//{%s}trkpt' % namespace_dict['ns'])
        if not trkpt_list:
            trkpt_list = root.findall('.//{%s}rtept' % namespace_dict['ns'])
    
    if not trkpt_list:
        trkpt_list = root.findall('.//trkpt')
        if not trkpt_list:
            trkpt_list = root.findall('.//rtept')
    
    if not trkpt_list:
        for elem in root.iter():
            if elem.tag.endswith('trkpt') or elem.tag.endswith('rtept'):
                trkpt_list.append(elem)
    
    for trkpt in trkpt_list:
        lat_str = trkpt.get('lat')
        lon_str = trkpt.get('lon')
        if lat_str is None or lon_str is None:
            continue  # Skip trackpoints without lat/lon
        lat = float(lat_str)
        lon = float(lon_str)
        
        ele_elem = None
        if namespace_dict:
            ele_elem = trkpt.find('{%s}ele' % namespace_dict['ns'])
        if ele_elem is None:
            ele_elem = trkpt.find('ele')
        
        elev = float(ele_elem.text) if ele_elem is not None and ele_elem.text else 0.0
        trackpoints.append((lat, lon, elev))
    
    return trackpoints

def calculate_total_distance(trackpoints):
    """Calculate total distance of route."""
    total_distance = 0.0
    for i in range(len(trackpoints) - 1):
        lat1, lon1, _ = trackpoints[i]
        lat2, lon2, _ = trackpoints[i + 1]
        total_distance += haversine_distance(lat1, lon1, lat2, lon2)
    return total_distance

def find_checkpoint_indices(trackpoints, checkpoint_distances):
    """Find trackpoint indices for checkpoints."""
    cumulative_dist = 0.0
    distances = [0.0]
    
    for i in range(len(trackpoints) - 1):
        lat1, lon1, _ = trackpoints[i]
        lat2, lon2, _ = trackpoints[i + 1]
        cumulative_dist += haversine_distance(lat1, lon1, lat2, lon2)
        distances.append(cumulative_dist)
    
    checkpoint_indices = [0]
    
    for cp_dist in checkpoint_distances:
        closest_idx = min(range(len(distances)), 
                         key=lambda i: abs(distances[i] - cp_dist))
        checkpoint_indices.append(closest_idx)
    
    checkpoint_indices.append(len(trackpoints) - 1)
    
    return checkpoint_indices, distances

def calculate_elevation_change(trackpoints, start_idx, end_idx):
    """Calculate elevation gain and loss between indices."""
    gain = 0.0
    loss = 0.0
    
    for i in range(start_idx, end_idx):
        elev_change = trackpoints[i + 1][2] - trackpoints[i][2]
        if elev_change > 0:
            gain += elev_change
        else:
            loss += abs(elev_change)
    
    return gain, loss

def adjust_pace_for_elevation(base_pace, elevation_gain, elevation_loss, distance_km, 
                              cumulative_time_hours=0.0, elev_gain_factor=ELEVATION_GAIN_FACTOR,
                              fatigue_enabled=True, fatigue_multiplier=FATIGUE_MULTIPLIER,
                              difficulty='easy'):
    """Adjust pace for elevation, fatigue, and terrain difficulty."""
    if distance_km == 0:
        return base_pace, base_pace, 0.0, 0.0
    
    elev_time_seconds = (elevation_gain * elev_gain_factor) - (elevation_loss * elev_gain_factor * 0.3)
    elev_time_minutes = elev_time_seconds / 60.0
    
    segment_time_no_fatigue = (distance_km * base_pace) + elev_time_minutes
    pace_with_elev_only = segment_time_no_fatigue / distance_km if distance_km > 0 else base_pace
    
    min_allowed_pace = base_pace * (1.0 - MAX_DOWNHILL_SPEED_INCREASE / 100.0)
    pace_with_elev_limited = max(pace_with_elev_only, min_allowed_pace)
    
    # Apply fatigue only if enabled
    if fatigue_enabled:
        fatigue_factor = 1.0 + (cumulative_time_hours * fatigue_multiplier / 100.0)
        fatigued_pace = pace_with_elev_limited * fatigue_factor
        fatigue_seconds_per_km = (fatigued_pace - pace_with_elev_limited) * 60.0
    else:
        fatigued_pace = pace_with_elev_limited
        fatigue_seconds_per_km = 0.0
    
    # Apply difficulty adjustment (in seconds per km)
    # For technical terrain, apply different adjustments based on elevation change
    if difficulty == 'difficult':
        # Technical terrain: +10s/km for climbing, -20s/km for descending
        if elevation_gain > elevation_loss:
            difficulty_adjustment_seconds = DIFFICULTY_PACE_MAP.get('technical_uphill', 0)
        else:
            difficulty_adjustment_seconds = DIFFICULTY_PACE_MAP.get('technical_downhill', 0)
    else:
        difficulty_adjustment_seconds = DIFFICULTY_PACE_MAP.get(difficulty, 0)
    
    difficulty_adjustment_minutes = difficulty_adjustment_seconds / 60.0
    pace_with_difficulty = fatigued_pace + difficulty_adjustment_minutes
    
    max_allowed_pace = base_pace * 2.0
    final_pace = min(pace_with_difficulty, max_allowed_pace)
    pace_capped = pace_with_difficulty > max_allowed_pace
    
    return final_pace, pace_with_elev_limited, fatigue_seconds_per_km, difficulty_adjustment_seconds, pace_capped

def format_time(minutes):
    """Format minutes to HH:MM:SS."""
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    secs = int((minutes % 1) * 60)
    return f"{hours:02d}:{mins:02d}:{secs:02d}"

@app.route('/')
def index():
    """Render main page."""
    return render_template('index.html')

@app.route('/api/upload-gpx', methods=['POST'])
def upload_gpx():
    """Handle GPX file upload."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '' or file.filename is None:
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.endswith('.gpx'):
        return jsonify({'error': 'File must be a GPX file'}), 400
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    try:
        trackpoints = parse_gpx_file(filepath)
        total_distance = calculate_total_distance(trackpoints)
        
        # Calculate total elevation
        total_elev_gain = 0.0
        total_elev_loss = 0.0
        for i in range(len(trackpoints) - 1):
            elev_change = trackpoints[i + 1][2] - trackpoints[i][2]
            if elev_change > 0:
                total_elev_gain += elev_change
            else:
                total_elev_loss += abs(elev_change)
        
        return jsonify({
            'filename': filename,
            'total_distance': round(total_distance, 2),
            'total_distance_miles': round(total_distance * 0.621371, 2),
            'total_elev_gain': round(total_elev_gain, 0),
            'total_elev_loss': round(total_elev_loss, 0),
            'num_trackpoints': len(trackpoints)
        })
    except Exception as e:
        return jsonify({'error': f'Error parsing GPX file: {str(e)}'}), 400

@app.route('/api/calculate', methods=['POST'])
def calculate():
    """Calculate race plan."""
    try:
        data = request.json
        if data is None:
            return jsonify({'error': 'Invalid JSON data'}), 400
        
        # Get uploaded GPX file
        filename = data.get('gpx_filename')
        if not filename:
            return jsonify({'error': 'No GPX file specified'}), 400
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(filepath):
            return jsonify({'error': 'GPX file not found'}), 400
        
        # Parse inputs
        checkpoint_distances = data.get('checkpoint_distances', [])
        segment_difficulties = data.get('segment_difficulties', [])
        avg_cp_time = float(data.get('avg_cp_time', 5))
        z2_pace = float(data.get('z2_pace', 6.5))  # in minutes per km
        carbs_per_hour = float(data.get('carbs_per_hour', DEFAULT_CARBS_PER_HOUR))
        water_per_hour = float(data.get('water_per_hour', DEFAULT_WATER_PER_HOUR))
        elev_gain_factor = float(data.get('elev_gain_factor', ELEVATION_GAIN_FACTOR))
        race_start_time = data.get('race_start_time')  # "HH:MM" or None
        
        # Fatigue settings
        fatigue_enabled = data.get('fatigue_enabled', True)
        ability_level = data.get('ability_level', 'average')
        fatigue_multiplier = ABILITY_FATIGUE_MAP.get(ability_level, FATIGUE_MULTIPLIER)
        
        # Parse GPX
        trackpoints = parse_gpx_file(filepath)
        total_distance = calculate_total_distance(trackpoints)
        
        # Find checkpoint indices
        checkpoint_indices, distances = find_checkpoint_indices(trackpoints, checkpoint_distances)
        
        # Calculate segments
        segments = []
        cumulative_time = 0.0
        total_moving_time = 0.0
        
        num_checkpoints = len(checkpoint_distances)
        segment_labels = ["Start"]
        for i in range(num_checkpoints):
            segment_labels.append(f"CP{i + 1}")
        segment_labels.append("Finish")
        
        for i in range(len(checkpoint_indices) - 1):
            start_idx = checkpoint_indices[i]
            end_idx = checkpoint_indices[i + 1]
            
            segment_dist = distances[end_idx] - distances[start_idx]
            elev_gain, elev_loss = calculate_elevation_change(trackpoints, start_idx, end_idx)
            net_elev_change = elev_gain - elev_loss
            
            # Get difficulty for this segment (default to 'easy' if not provided)
            segment_difficulty = segment_difficulties[i] if i < len(segment_difficulties) else 'easy'
            
            cumulative_hours = total_moving_time / 60.0
            adjusted_pace, elev_adjusted_pace, fatigue_seconds, difficulty_seconds, pace_capped = adjust_pace_for_elevation(
                z2_pace, elev_gain, elev_loss, segment_dist, cumulative_hours, elev_gain_factor,
                fatigue_enabled, fatigue_multiplier, segment_difficulty
            )
            
            # Log when pace is capped
            if pace_capped:
                segment_label = f"{segment_labels[i]} → {segment_labels[i + 1]}"
                print(f"⚠️  PACE CAPPED: {segment_label} - Pace limited to {adjusted_pace:.2f} min/km (2× base pace)")
            
            segment_time = segment_dist * adjusted_pace
            total_moving_time += segment_time
            
            if i > 0:
                cumulative_time += avg_cp_time
            
            cumulative_time += segment_time
            
            segment_hours = segment_time / 60.0
            target_carbs = round((segment_hours * carbs_per_hour) / 10) * 10
            target_water_L = round((segment_hours * water_per_hour / 1000) * 10) / 10
            
            # Calculate time of day
            time_of_day = None
            if race_start_time:
                try:
                    start_hours, start_minutes = map(int, race_start_time.split(':'))
                    start_total_minutes = start_hours * 60 + start_minutes
                    current_total_minutes = start_total_minutes + cumulative_time
                    current_hours = int(current_total_minutes // 60) % 24
                    current_mins = int(current_total_minutes % 60)
                    time_of_day = f"{current_hours:02d}:{current_mins:02d}"
                except:
                    pass
            
            # Format difficulty string
            if difficulty_seconds > 0:
                difficulty_str = f"+{int(difficulty_seconds // 60)}:{int(difficulty_seconds % 60):02d}"
            elif difficulty_seconds < 0:
                difficulty_str = f"-{int(abs(difficulty_seconds) // 60)}:{int(abs(difficulty_seconds) % 60):02d}"
            else:
                difficulty_str = "0:00"
            
            segments.append({
                'from': segment_labels[i],
                'to': segment_labels[i + 1],
                'distance': round(segment_dist, 2),
                'elev_gain': round(elev_gain, 0),
                'elev_loss': round(elev_loss, 0),
                'net_elev': round(net_elev_change, 0),
                'elev_pace': round(elev_adjusted_pace, 2),
                'elev_pace_str': f"{int(elev_adjusted_pace)}:{int((elev_adjusted_pace % 1) * 60):02d}",
                'pace': round(adjusted_pace, 2),
                'pace_str': f"{int(adjusted_pace)}:{int((adjusted_pace % 1) * 60):02d}",
                'pace_capped': pace_capped,
                'fatigue_seconds': round(fatigue_seconds, 1),
                'fatigue_str': f"+{int(fatigue_seconds // 60)}:{int(fatigue_seconds % 60):02d}",
                'difficulty_seconds': round(difficulty_seconds, 1),
                'difficulty_str': difficulty_str,
                'segment_time': round(segment_time, 2),
                'segment_time_str': format_time(segment_time),
                'cumulative_time': round(cumulative_time, 2),
                'cumulative_time_str': format_time(cumulative_time),
                'target_carbs': target_carbs,
                'target_water': target_water_L,
                'time_of_day': time_of_day
            })
        
        # Calculate totals
        total_elev_gain = sum(s['elev_gain'] for s in segments)
        total_carbs = sum(s['target_carbs'] for s in segments)
        total_water = sum(s['target_water'] for s in segments)
        total_cp_time = avg_cp_time * num_checkpoints
        
        # Build elevation profile data
        elevation_profile = []
        cumulative_dist = 0.0
        for i in range(len(trackpoints)):
            if i > 0:
                lat1, lon1, _ = trackpoints[i - 1]
                lat2, lon2, _ = trackpoints[i]
                cumulative_dist += haversine_distance(lat1, lon1, lat2, lon2)
            elevation_profile.append({
                'distance': round(cumulative_dist, 3),
                'elevation': round(trackpoints[i][2], 1)
            })
        
        # Sample elevation data for performance (max 500 points)
        if len(elevation_profile) > 500:
            step = len(elevation_profile) // 500
            elevation_profile = elevation_profile[::step]
        
        return jsonify({
            'segments': segments,
            'elevation_profile': elevation_profile,
            'summary': {
                'total_distance': round(total_distance, 2),
                'total_moving_time': round(total_moving_time, 2),
                'total_moving_time_str': format_time(total_moving_time),
                'total_cp_time': round(total_cp_time, 2),
                'total_cp_time_str': format_time(total_cp_time),
                'total_race_time': round(cumulative_time, 2),
                'total_race_time_str': format_time(cumulative_time),
                'total_elev_gain': total_elev_gain,
                'total_carbs': total_carbs,
                'total_water': round(total_water, 1)
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/save-plan', methods=['POST'])
def save_plan():
    """Save race plan."""
    try:
        data = request.json
        if data is None:
            return jsonify({'error': 'Invalid JSON data'}), 400
        plan_name = data.get('plan_name', f"race_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        # Sanitize filename
        plan_name = secure_filename(plan_name)
        if not plan_name.endswith('.json'):
            plan_name += '.json'
        
        filepath = os.path.join(app.config['SAVED_PLANS_FOLDER'], plan_name)
        
        # Include elevation_profile in saved data
        save_data = {
            'plan_name': data.get('plan_name'),
            'gpx_filename': data.get('gpx_filename'),
            'checkpoint_distances': data.get('checkpoint_distances', []),
            'segment_difficulties': data.get('segment_difficulties', []),
            'avg_cp_time': data.get('avg_cp_time'),
            'z2_pace': data.get('z2_pace'),
            'elev_gain_factor': data.get('elev_gain_factor'),
            'carbs_per_hour': data.get('carbs_per_hour'),
            'water_per_hour': data.get('water_per_hour'),
            'race_start_time': data.get('race_start_time'),
            'fatigue_enabled': data.get('fatigue_enabled'),
            'ability_level': data.get('ability_level'),
            'segments': data.get('segments'),
            'summary': data.get('summary'),
            'elevation_profile': data.get('elevation_profile')
        }
        
        with open(filepath, 'w') as f:
            json.dump(save_data, f, indent=2)
        
        return jsonify({'message': 'Plan saved successfully', 'filename': plan_name})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/list-plans', methods=['GET'])
def list_plans():
    """List all saved race plans."""
    try:
        plans = []
        for filename in os.listdir(app.config['SAVED_PLANS_FOLDER']):
            if filename.endswith('.json'):
                filepath = os.path.join(app.config['SAVED_PLANS_FOLDER'], filename)
                modified_time = os.path.getmtime(filepath)
                plans.append({
                    'filename': filename,
                    'name': filename.replace('.json', ''),
                    'modified': datetime.fromtimestamp(modified_time).strftime('%Y-%m-%d %H:%M:%S')
                })
        
        plans.sort(key=lambda x: x['modified'], reverse=True)
        return jsonify({'plans': plans})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/load-plan/<filename>', methods=['GET'])
def load_plan(filename):
    """Load a saved race plan."""
    try:
        filepath = os.path.join(app.config['SAVED_PLANS_FOLDER'], secure_filename(filename))
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'Plan not found'}), 404
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/delete-plan/<filename>', methods=['DELETE'])
def delete_plan(filename):
    """Delete a saved race plan."""
    try:
        filepath = os.path.join(app.config['SAVED_PLANS_FOLDER'], secure_filename(filename))
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'Plan not found'}), 404
        
        os.remove(filepath)
        return jsonify({'message': 'Plan deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/export-csv', methods=['POST'])
def export_csv():
    """Export race plan to CSV."""
    try:
        data = request.json
        if data is None:
            return jsonify({'error': 'Invalid JSON data'}), 400
        segments = data.get('segments', [])
        summary = data.get('summary', {})
        race_start_time = data.get('race_start_time')
        
        # Generate CSV
        csv_filename = f"race_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        csv_path = os.path.join(app.config['UPLOAD_FOLDER'], csv_filename)
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Header
            header = ['Segment', 'Distance (km)', 'Elev Gain (m)', 'Elev Loss (m)', 'Net Elev (m)', 
                     'Elev Pace (min/km)', 'Fatigue (mm:ss)', 'Difficulty (mm:ss)', 'Final Pace (min/km)', 
                     'Segment Time', 'Carbs (g)', 'Water (L)', 'Cumulative Time']
            if race_start_time:
                header.append('Time of Arrival at CP')
            writer.writerow(header)
            
            # Data rows
            for seg in segments:
                # Extract checkpoint name from segment 'to' field for dynamic column naming
                checkpoint_name = seg['to']
                row = [
                    f"{seg['from']} → {seg['to']}",
                    seg['distance'],
                    seg['elev_gain'],
                    seg['elev_loss'],
                    seg['net_elev'],
                    seg['elev_pace_str'],
                    seg['fatigue_str'],
                    seg.get('difficulty_str', '0:00'),
                    seg['pace_str'],
                    seg['segment_time_str'],
                    seg['target_carbs'],
                    seg['target_water'],
                    seg['cumulative_time_str']
                ]
                if race_start_time:
                    row.append(seg.get('time_of_day', ''))
                writer.writerow(row)
            
            # Summary
            writer.writerow([])
            writer.writerow(['SUMMARY'])
            writer.writerow(['Total Moving Time', summary.get('total_moving_time_str')])
            writer.writerow(['Total CP Time', summary.get('total_cp_time_str')])
            writer.writerow(['Total Race Time', summary.get('total_race_time_str')])
            writer.writerow(['Total Distance (km)', summary.get('total_distance')])
            writer.writerow(['Total Elev Gain (m)', summary.get('total_elev_gain')])
            writer.writerow(['Total Carbs (g)', summary.get('total_carbs')])
            writer.writerow(['Total Water (L)', summary.get('total_water')])
        
        return send_file(csv_path, as_attachment=True, download_name=csv_filename)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
