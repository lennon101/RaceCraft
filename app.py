"""
RaceCraft - Fuel & Pacing Planner
Version: v1.3.4
Release Date: January 30, 2026

Major Changes in v1.3.4:
- fix decimal input validation for numeric fields
    - Change input type from 'number' to 'text' for all decimal-input fields
    - Fields updated: avg-cp-time, carbs-per-hour, water-per-hour, carbs-per-gel, checkpoint-distances
    - Enables proper JavaScript control over decimal input without browser interference

Major Changes in v1.3.3:
- fix decimal input for checkpoint distances
    - Change input type from 'number' to 'text' to allow JavaScript full control
    - Maintain pattern and inputmode for mobile keyboard support

Major changes in v1.3.2:
- Validation Rules Implemented:
    - Real Numbers: Inputs must be valid positive numbers
    - Distance Limits: Cannot exceed total route distance
    - No Duplicates: All checkpoint distances must be unique
    - Ascending Order: CP2 > CP1, CP3 > CP2, etc.
    - Immediate Feedback: Errors show instantly with visual indicators
- Keep user informed and prevent invalid submissions to input fields 

Major Changes in v1.3.1:
- quick fix to resolve port issues with docker file 

Major Changes in v1.3.0:
- CSV export now doesn't leave behind temporary files on the server 
- Single parent directory for data storage, configurable via environment variables 

Major Changes in v1.2.2:
- Add drop bag plan to each of the tooltip hovers in the elevation profile plot #26
- Fix incorrect gel count in drop bag plan when carbs per gel is specified 
- Fix incorrect hover info tooltip for skill level in index.html
- Update export_csv function to improve checkpoint naming format in CSV output

Major Changes in v1.2.1:
- Update skill level descriptions in index.html for clarity and improved user guidance
- Update technical skill level descriptions and options in index.html
- Update GPX upload handling to display distance and elevation gain, and fetch elevation profile
- Add iOS Home Screen and PWA meta tags for improved app integration (issue #23)
- Update header background color and adjust subtitle opacity
- Remove background from logo and update CSS styling for header text
- Update fav-icon to circle

"""

from flask import Flask, render_template, request, jsonify, send_file, send_from_directory, after_this_request
import xml.etree.ElementTree as ET
import math
import io
import csv
from datetime import datetime
from werkzeug.utils import secure_filename
import json
import os
import platform
from functools import wraps
from dotenv import load_dotenv
from whitenoise import WhiteNoise

# Load environment variables
load_dotenv()

# Supabase Configuration
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')

# Initialize Supabase client if credentials are provided
supabase_client = None
supabase_admin_client = None
supabase_import_available = False

if SUPABASE_URL and SUPABASE_ANON_KEY:
    try:
        from supabase import create_client, Client
        supabase_import_available = True
        # Don't create clients at startup - do it lazily
        # This prevents failures from invalid credentials blocking the app
        print("✓ Supabase credentials loaded - authentication enabled")
        print(f"  URL: {SUPABASE_URL}")
        anon_key_preview = SUPABASE_ANON_KEY[:20] + "..." if len(SUPABASE_ANON_KEY) > 20 else SUPABASE_ANON_KEY
        print(f"  Anon key: {anon_key_preview}")
    except ImportError as e:
        print(f"⚠ Warning: Failed to import Supabase client library: {e}")
        print("  App will run in legacy file-based mode")
        print("  Make sure 'supabase' is installed: pip install supabase")
        SUPABASE_URL = None
        SUPABASE_ANON_KEY = None
else:
    print("⚠ Warning: Supabase credentials not found in environment variables")
    print("  App will run in legacy file-based mode")
    print("  Set SUPABASE_URL and SUPABASE_ANON_KEY to enable authentication")

app = Flask(__name__)

# Configure WhiteNoise for static file serving in production
app.wsgi_app = WhiteNoise(app.wsgi_app, root='static/', prefix='static/')

# Configure paths - use local paths for development, Docker paths for production
if os.environ.get('FLASK_ENV') == 'production' or os.path.exists('/app'):
    # Docker/production environment
    app.config['UPLOAD_FOLDER'] = '/app/data/uploads'
    app.config['SAVED_PLANS_FOLDER'] = '/app/data/saved_plans'
else:
    # Local development environment
    app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'FuelPlanData', 'uploads')
    app.config['SAVED_PLANS_FOLDER'] = os.path.join(os.getcwd(), 'FuelPlanData', 'saved_plans')

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['SAVED_PLANS_FOLDER'], exist_ok=True)

# Constants
DEFAULT_CARBS_PER_HOUR = 60.0
DEFAULT_WATER_PER_HOUR = 500.0

# Climbing ability parameters - vertical speed in m/h
# Updated to more realistic values for mountain runners
CLIMBING_ABILITY_PARAMS = {
    'conservative': {'vertical_speed': 600, 'label': 'Conservative Climber'},   # Untrained/cautious
    'moderate': {'vertical_speed': 800, 'label': 'Moderate Climber'},           # Recreational mountain runner
    'strong': {'vertical_speed': 1000, 'label': 'Strong Climber'},              # Experienced/trained
    'very_strong': {'vertical_speed': 1250, 'label': 'Very Strong Climber'},    # Competitive
    'elite': {'vertical_speed': 1500, 'label': 'Elite Climber'}                 # Top-level mountain athlete
}

# Downhill speed multipliers by gradient range (as decimal, e.g., 0.05 = 5%)
# Values represent speed multiplier relative to flat pace
DOWNHILL_SPEED_MULTIPLIERS = {
    'gentle': {'gradient_max': 0.05, 'multiplier': 1.05},     # 0-5%: slight speedup
    'moderate': {'gradient_max': 0.10, 'multiplier': 1.15},   # 5-10%: moderate speedup
    'steep': {'gradient_max': 0.15, 'multiplier': 1.20},      # 10-15%: max efficient speedup
    'very_steep': {'gradient_max': 1.0, 'multiplier': 1.10}   # >15%: forced to slow down
}

# Fitness level parameters - Fatigue Onset Point (FOP) in km-effort
# Reduced alpha and beta values to prevent excessive fatigue escalation
# Beta ≤ 1.0 provides linear or sub-linear growth (more realistic for endurance events)
FITNESS_LEVEL_PARAMS = {
    'untrained': {'fop': 25, 'alpha': 0.12, 'beta': 1.0},      # 12% per 1x FOP beyond threshold
    'recreational': {'fop': 37.5, 'alpha': 0.10, 'beta': 1.0}, # 10% per 1x FOP beyond threshold
    'trained': {'fop': 55, 'alpha': 0.08, 'beta': 0.95},       # 8% per 1x FOP, slight sub-linear
    'elite': {'fop': 75, 'alpha': 0.06, 'beta': 0.90}          # 6% per 1x FOP, more sub-linear
}

# Terrain Efficiency Factors (TEF) - multipliers where 1.0 = smooth ideal trail
# Higher values = slower pace due to terrain difficulty
TERRAIN_FACTORS = {
    'road': 0.95,              # Road/track
    'smooth_trail': 1.0,       # Smooth singletrack (ideal baseline)
    'dirt_road': 1.05,         # Dirt road
    'rocky_runnable': 1.15,    # Rocky but runnable (average of 1.1-1.2)
    'technical': 1.325,        # Technical trail with roots/rocks (average of 1.25-1.4)
    'very_technical': 1.65,    # Very technical or hands-needed (average of 1.5-1.8)
    'scrambling': 2.0          # Scrambling or unstable footing
}

# Terrain gradient scaling factor (gamma) - how much gradient amplifies terrain effects
TERRAIN_GRADIENT_GAMMA = 1.25  # Between 1.0-1.5 as recommended

# Terrain effect on climbs vs descents
TERRAIN_CLIMB_FACTOR = 0.7     # 70% effect on climbs
TERRAIN_DESCENT_FACTOR = 1.0   # 100% effect on descents


# Authentication Helper Functions
def get_user_from_token(auth_header):
    """Extract and validate user from authorization header."""
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    
    if not supabase_client:
        return None
    
    client = get_supabase_client()
    if not client:
        return None
    
    try:
        token = auth_header.replace('Bearer ', '')
        user = client.auth.get_user(token)
        return user
    except Exception as e:
        print(f"Error validating token: {e}")
        return None


def get_user_id_from_request():
    """Get user ID from request, supporting both authenticated and anonymous users."""
    auth_header = request.headers.get('Authorization')
    
    # Try to get authenticated user
    if auth_header and supabase_client:
        user = get_user_from_token(auth_header)
        if user and hasattr(user, 'user') and user.user:
            return {'type': 'authenticated', 'id': user.user.id}
    
    # Fall back to anonymous ID from request
    anonymous_id = request.headers.get('X-Anonymous-ID')
    if anonymous_id:
        return {'type': 'anonymous', 'id': anonymous_id}
    
    return None


def require_user_or_anonymous(f):
    """Decorator to require either authenticated user or anonymous ID."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_info = get_user_id_from_request()
        if not user_info:
            return jsonify({'error': 'Authentication or anonymous ID required'}), 401
        return f(*args, user_info=user_info, **kwargs)
    return decorated_function


def is_supabase_enabled():
    """Check if Supabase is properly configured."""
    # Check if we have credentials, not if client is initialized
    # This allows frontend to handle connection even if backend client failed
    return SUPABASE_URL is not None and SUPABASE_ANON_KEY is not None

def get_supabase_client():
    """Get or create the Supabase client."""
    global supabase_client
    if supabase_client is None and is_supabase_enabled() and supabase_import_available:
        try:
            from supabase import create_client
            supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        except Exception as e:
            print(f"Failed to create Supabase client: {e}")
            return None
    return supabase_client

def get_supabase_admin_client():
    """Get or create the Supabase admin client."""
    global supabase_admin_client
    if supabase_admin_client is None and is_supabase_enabled() and supabase_import_available and SUPABASE_SERVICE_KEY:
        try:
            from supabase import create_client
            supabase_admin_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        except Exception as e:
            print(f"Failed to create Supabase admin client: {e}")
            return None
    return supabase_admin_client

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

def find_checkpoint_indices_from_profile(elevation_profile, checkpoint_distances):
    """Find checkpoint indices when using elevation profile data."""
    distances = [point['distance'] for point in elevation_profile]
    
    checkpoint_indices = [0]
    
    for cp_dist in checkpoint_distances:
        closest_idx = min(range(len(distances)), 
                         key=lambda i: abs(distances[i] - cp_dist))
        checkpoint_indices.append(closest_idx)
    
    checkpoint_indices.append(len(elevation_profile) - 1)
    
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

def calculate_terrain_efficiency_factor(terrain_type='smooth_trail', gradient=0.0, 
                                       skill_level=0.5, is_descent=False):
    """
    Calculate terrain efficiency factor (TEF) for a segment.
    
    Args:
        terrain_type: Type of terrain (key from TERRAIN_FACTORS)
        gradient: Segment gradient as decimal (e.g., 0.1 = 10% grade)
        skill_level: Athlete technical skill (0.0 = novice, 1.0 = expert)
        is_descent: Whether segment is primarily descending
        
    Returns:
        Terrain efficiency factor (≥ 1.0, where 1.0 = no terrain penalty)
    """
    # Get base terrain factor
    base_terrain_factor = TERRAIN_FACTORS.get(terrain_type, 1.0)
    
    # Scale terrain impact by gradient: effective_terrain_factor = terrain_factor × (1 + γ × |gradient|)
    gradient_scaling = 1.0 + (TERRAIN_GRADIENT_GAMMA * abs(gradient))
    scaled_terrain_factor = base_terrain_factor * gradient_scaling
    
    # Apply different terrain effects for climbs vs descents
    if is_descent:
        # 100% effect on descents
        direction_adjusted_factor = 1.0 + (scaled_terrain_factor - 1.0) * TERRAIN_DESCENT_FACTOR
    else:
        # ~70% effect on climbs
        direction_adjusted_factor = 1.0 + (scaled_terrain_factor - 1.0) * TERRAIN_CLIMB_FACTOR
    
    # Adjust for athlete technical skill: adjusted = 1 + (factor − 1) × (1 − skill)
    skill_adjusted_factor = 1.0 + (direction_adjusted_factor - 1.0) * (1.0 - skill_level)
    
    # Ensure factor is at least 1.0 (terrain can only slow down, not speed up beyond smooth trail)
    return max(1.0, skill_adjusted_factor)

def calculate_vertical_speed(base_vertical_speed, gradient, skill_level=0.5):
    """
    Calculate gradient-aware vertical speed in m/h.
    
    Vertical speed efficiency varies with gradient:
    - <3%: Minimal efficiency penalty (90% - barely feels like climbing)
    - 3-6%: Slight reduction (90-95% - gentle sustained climb)
    - 6-12%: Peak efficiency (95-100% - optimal climbing zone)
    - 12-18%: Still efficient (95-85% - steep but manageable)
    - >18%: Declining efficiency (85-70% - very steep, forced to slow)
    
    Technical skill improves climbing efficiency, especially on steep grades.
    
    Args:
        base_vertical_speed: Athlete's base vertical speed in m/h
        gradient: Grade as decimal (e.g., 0.10 = 10%)
        skill_level: Athlete technical skill (0.0 = novice, 1.0 = expert)
        
    Returns:
        Adjusted vertical speed in m/h
    """
    gradient_pct = abs(gradient) * 100.0
    
    # Efficiency multiplier based on gradient
    if gradient_pct < 3.0:
        # Very gentle: 90% efficiency (barely noticeable)
        efficiency = 0.90
    elif gradient_pct < 6.0:
        # Gentle: scale from 90% to 95%
        efficiency = 0.90 + (gradient_pct - 3.0) / 3.0 * 0.05
    elif gradient_pct <= 12.0:
        # Optimal climbing zone: scale from 95% to 100%
        efficiency = 0.95 + (gradient_pct - 6.0) / 6.0 * 0.05
    elif gradient_pct <= 18.0:
        # Steep but efficient: scale from 100% to 85%
        efficiency = 1.0 - (gradient_pct - 12.0) / 6.0 * 0.15
    elif gradient_pct <= 25.0:
        # Very steep: scale from 85% to 70%
        efficiency = 0.85 - (gradient_pct - 18.0) / 7.0 * 0.15
    else:
        # Extremely steep: 70% efficiency
        efficiency = 0.70
    
    # Technical skill improves climbing efficiency on steeper grades
    # On steep climbs (>12%), skilled runners maintain better technique
    # Bonus scales from 0% (novice) to 5% (expert) on very steep terrain
    if gradient_pct > 12.0:
        skill_bonus = skill_level * 0.05 * min(1.0, (gradient_pct - 12.0) / 13.0)
        efficiency = min(1.0, efficiency + skill_bonus)
    
    return base_vertical_speed * efficiency

def calculate_downhill_multiplier(gradient, terrain_type='smooth_trail', skill_level=0.5):
    """
    Calculate downhill speed multiplier based on gradient.
    
    Downhills are modeled separately from climbs using speed multipliers
    rather than negative penalties. Speed is capped by terrain and gradient.
    Technical skill affects how confidently and quickly an athlete can descend.
    
    Args:
        gradient: Grade as decimal (negative for downhill, e.g., -0.10 = -10%)
        terrain_type: Type of terrain (affects maximum safe downhill speed)
        skill_level: Athlete technical skill (0.0 = novice, 1.0 = expert)
        
    Returns:
        Speed multiplier (≥1.0, where 1.0 = flat pace)
    """
    if gradient >= 0:
        return 1.0  # Not a downhill
    
    gradient_pct = abs(gradient) * 100.0
    
    # Base multiplier by gradient
    if gradient_pct <= 5.0:
        base_multiplier = 1.05
    elif gradient_pct <= 10.0:
        base_multiplier = 1.15
    elif gradient_pct <= 15.0:
        base_multiplier = 1.20  # Max efficient downhill speed
    else:
        # Very steep: forced to slow down
        base_multiplier = 1.10
    
    # Terrain limits maximum downhill speed
    # Novice runners are more cautious, experts can push limits
    terrain_downhill_caps_base = {
        'road': 1.0,              # Full speed possible
        'smooth_trail': 0.95,     # Slight reduction
        'dirt_road': 0.90,        # More caution needed
        'rocky_runnable': 0.80,   # Significant caution
        'technical': 0.70,        # Must slow considerably
        'very_technical': 0.60,   # Very slow descent
        'scrambling': 0.50        # Extremely slow descent
    }
    
    base_terrain_cap = terrain_downhill_caps_base.get(terrain_type, 0.90)
    
    # Skill level increases the terrain cap - experts can descend faster on technical terrain
    # skill_bonus ranges from 0 (novice) to 30% of remaining headroom (expert)
    # This means on technical terrain (0.70 cap), expert gets: 0.70 + 0.3 * (1.0 - 0.70) = 0.79
    skill_bonus = skill_level * 0.3 * (1.0 - base_terrain_cap)
    terrain_cap = min(1.0, base_terrain_cap + skill_bonus)
    
    # Apply terrain cap: multiplier_adjusted = 1 + (multiplier - 1) × terrain_cap
    adjusted_multiplier = 1.0 + (base_multiplier - 1.0) * terrain_cap
    
    return adjusted_multiplier

def adjust_pace_for_elevation(base_pace, elevation_gain, elevation_loss, distance_km, 
                              cumulative_effort=0.0, climbing_ability='moderate',
                              fatigue_enabled=True, fitness_level='recreational',
                              terrain_type='smooth_trail', skill_level=0.5):
    """
    Calculate segment time using additive climbing model with vertical speed.
    
    Model: segment_time = horizontal_time + climb_time + descent_time
    where:
      - horizontal_time = distance_km / (60 / base_pace) * 60  [minutes]
      - climb_time = ascent_m / vertical_speed * 60  [minutes]
      - descent_time uses downhill speed multiplier
    
    All times are then scaled by fatigue and terrain multipliers.
    
    Args:
        base_pace: Flat pace in min/km
        elevation_gain: Ascent in meters
        elevation_loss: Descent in meters
        distance_km: Horizontal distance in km
        cumulative_effort: Cumulative effort in km-effort (for fatigue)
        climbing_ability: Athlete climbing ability key
        fatigue_enabled: Whether to apply fatigue
        fitness_level: Athlete fitness level
        terrain_type: Type of terrain
        skill_level: Technical skill (0.0-1.0)
        
    Returns:
        Tuple: (final_pace, base_pace_with_climbing, fatigue_seconds, terrain_factor, pace_capped)
    """
    if distance_km == 0:
        return base_pace, base_pace, 0.0, 1.0, False
    
    # Get climbing parameters
    climb_params = CLIMBING_ABILITY_PARAMS.get(climbing_ability, CLIMBING_ABILITY_PARAMS['moderate'])
    base_vertical_speed = climb_params['vertical_speed']
    
    # Calculate gradient for gradient-aware adjustments
    net_elevation_change = elevation_gain - elevation_loss
    gradient = (net_elevation_change / (distance_km * 1000.0)) if distance_km > 0 else 0.0
    
    # Determine if segment is primarily descent
    is_descent = elevation_loss > elevation_gain
    
    # === Calculate base segment time using additive model ===
    
    # 1. Horizontal movement time (minutes)
    flat_speed_kmh = 60.0 / base_pace  # Convert min/km to km/h
    horizontal_time = (distance_km / flat_speed_kmh) * 60.0  # minutes
    
    # 2. Climbing time (minutes)
    if elevation_gain > 0:
        adjusted_vertical_speed = calculate_vertical_speed(base_vertical_speed, gradient, skill_level)
        climb_time = (elevation_gain / adjusted_vertical_speed) * 60.0  # minutes
    else:
        climb_time = 0.0
    
    # 3. Descent time adjustment (minutes)
    if elevation_loss > 0 and is_descent:
        downhill_multiplier = calculate_downhill_multiplier(gradient, terrain_type, skill_level)
        # Descent saves time: reduce horizontal time proportionally
        descent_time_savings = horizontal_time * (1.0 - 1.0 / downhill_multiplier)
    else:
        descent_time_savings = 0.0
    
    # Total base segment time
    base_segment_time = horizontal_time + climb_time - descent_time_savings
    
    # Calculate pace with climbing (for reporting)
    pace_with_climbing = base_segment_time / distance_km if distance_km > 0 else base_pace
    
    # === Apply terrain efficiency factor ===
    terrain_factor = calculate_terrain_efficiency_factor(
        terrain_type=terrain_type,
        gradient=gradient,
        skill_level=skill_level,
        is_descent=is_descent
    )
    
    # === Apply general skill efficiency bonus ===
    # Skilled runners are more efficient in all conditions (better form, foot placement, etc.)
    # This provides 0-3% improvement from novice to expert
    skill_efficiency_bonus = 1.0 - (skill_level * 0.03)
    
    # === Apply fatigue multiplier ===
    fatigue_multiplier = 1.0
    if fatigue_enabled:
        params = FITNESS_LEVEL_PARAMS.get(fitness_level, FITNESS_LEVEL_PARAMS['recreational'])
        fop = params['fop']
        alpha = params['alpha']
        beta = params['beta']
        
        # No fatigue penalty until cumulative effort exceeds FOP
        if cumulative_effort > fop:
            # Non-linear fatigue: fatigue_multiplier = 1 + α × ((E − FOP) / FOP)^β
            fatigue_multiplier = 1.0 + alpha * (((cumulative_effort - fop) / fop) ** beta)
    
    # === Combine all factors ===
    # segment_time = base_time × terrain_factor × fatigue_multiplier × skill_efficiency
    adjusted_segment_time = base_segment_time * terrain_factor * fatigue_multiplier * skill_efficiency_bonus
    final_pace = adjusted_segment_time / distance_km
    
    # Calculate fatigue penalty in seconds per km (for reporting)
    fatigue_seconds_per_km = (pace_with_climbing * fatigue_multiplier - pace_with_climbing) * 60.0
    
    # Apply reasonable max pace limit (2.5× base pace to accommodate very long races)
    # This prevents unrealistic slowdowns while still capping extreme values
    max_allowed_pace = base_pace * 2.5
    pace_capped = final_pace > max_allowed_pace
    if pace_capped:
        final_pace = max_allowed_pace
    
    return final_pace, pace_with_climbing, fatigue_seconds_per_km, terrain_factor, pace_capped

def format_time(minutes):
    """Format minutes to HH:MM:SS."""
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    secs = int((minutes % 1) * 60)
    return f"{hours:02d}:{mins:02d}:{secs:02d}"

def calculate_dropbag_contents(segments, checkpoint_dropbags, carbs_per_gel=None):
    """
    Calculate dropbag contents for each checkpoint with a dropbag, plus starting supplies.
    
    Logic:
    - Include a "Start" entry for the first segment (Start -> CP1)
    - If a checkpoint has a dropbag, it contains carbs/hydration for the next segment(s)
      until the next checkpoint with a dropbag.
    - If a checkpoint doesn't have a dropbag, accumulate to the previous checkpoint with a dropbag.
    
    Note: Runners pick up supplies from dropbags at checkpoints and carry them for upcoming segments.
    The first segment (Start -> CP1) uses starting supplies that must be packed before the race.
    
    Args:
        segments: List of calculated segments with target_carbs and target_water
        checkpoint_dropbags: List of booleans indicating which checkpoints have dropbags
        carbs_per_gel: Optional carbs per gel/sachet in grams. If provided, calculates gel quantities.
        
    Returns:
        List of dropbag contents: [{'checkpoint': 'Start', 'carbs': 20, 'hydration': 0.2},
                                     {'checkpoint': 'CP1', 'carbs': 120, 'hydration': 1.5, 
                                      'num_gels': 5, 'actual_carbs': 125}, ...]
    """
    dropbag_contents = []
    
    # Always include Start segment (segment 0: Start -> CP1)
    if segments and len(segments) > 0:
        start_segment = segments[0]
        carb_target = round(start_segment['target_carbs'])
        
        start_item = {
            'checkpoint': 'Start',
            'carbs': carb_target,
            'hydration': round(start_segment['target_water'], 1)
        }
        
        # Add gel calculations if carbs_per_gel is provided
        if carbs_per_gel and carbs_per_gel > 0:
            num_gels = round(carb_target / carbs_per_gel)
            actual_carbs = round(num_gels * carbs_per_gel, 2)
            start_item['num_gels'] = num_gels
            start_item['actual_carbs'] = actual_carbs
        
        dropbag_contents.append(start_item)
    
    # If no checkpoints have dropbags, only return Start
    if not checkpoint_dropbags or len(checkpoint_dropbags) == 0:
        return dropbag_contents
    
    # Build a mapping of checkpoint index to their dropbag contents
    # dropbag_accumulation[cp_index] = {'carbs': X, 'hydration': Y}
    dropbag_accumulation = {}
    
    # Initialize dropbag checkpoints
    for i, has_dropbag in enumerate(checkpoint_dropbags):
        if has_dropbag:
            dropbag_accumulation[i] = {'carbs': 0, 'hydration': 0.0}
    
    # If no dropbags are checked, return only Start
    if not dropbag_accumulation:
        return dropbag_contents
    
    # Iterate through segments and accumulate nutrition
    # Segments: Start -> CP1 (seg 0), CP1 -> CP2 (seg 1), ..., CPn -> Finish (seg n)
    for seg_idx, segment in enumerate(segments):
        # Skip the first segment (Start -> CP1) - already handled above
        if seg_idx == 0:
            continue
        
        # seg_idx corresponds to: seg 1 = CP1->CP2, seg 2 = CP2->CP3, etc.
        # The checkpoint that would carry this segment's nutrition is at index seg_idx - 1
        checkpoint_idx = seg_idx - 1
        
        # Find the last checkpoint with a dropbag at or before this checkpoint
        target_dropbag_cp = None
        for i in range(checkpoint_idx, -1, -1):
            if i in dropbag_accumulation:
                target_dropbag_cp = i
                break
        
        # If we found a dropbag checkpoint, accumulate this segment's nutrition
        if target_dropbag_cp is not None:
            dropbag_accumulation[target_dropbag_cp]['carbs'] += segment['target_carbs']
            dropbag_accumulation[target_dropbag_cp]['hydration'] += segment['target_water']
    
    # Convert to output format
    for cp_idx in sorted(dropbag_accumulation.keys()):
        contents = dropbag_accumulation[cp_idx]
        carb_target = round(contents['carbs'])  # Round to whole grams
        
        dropbag_item = {
            'checkpoint': f'CP{cp_idx + 1}',
            'carbs': carb_target,
            'hydration': round(contents['hydration'], 1)
        }
        
        # Add gel calculations if carbs_per_gel is provided
        if carbs_per_gel and carbs_per_gel > 0:
            num_gels = round(carb_target / carbs_per_gel)  # Round to nearest whole number
            actual_carbs = round(num_gels * carbs_per_gel, 2)
            dropbag_item['num_gels'] = num_gels
            dropbag_item['actual_carbs'] = actual_carbs
        
        dropbag_contents.append(dropbag_item)
    
    return dropbag_contents

@app.route('/')
def index():
    """Render main page."""
    return render_template('index.html')

@app.route('/robots.txt')
def robots():
    """Serve robots.txt file."""
    return send_from_directory('static', 'robots.txt', mimetype='text/plain')

@app.route('/api/upload-gpx', methods=['POST'])
def upload_gpx():
    """Handle GPX file upload."""
    from werkzeug.utils import secure_filename
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
        
        # Parse inputs
        checkpoint_distances = data.get('checkpoint_distances', [])
        checkpoint_dropbags = data.get('checkpoint_dropbags', [])  # New: dropbag status
        segment_terrain_types = data.get('segment_terrain_types', [])
        avg_cp_time = float(data.get('avg_cp_time', 5))
        z2_pace = float(data.get('z2_pace', 6.5))  # in minutes per km
        carbs_per_hour = float(data.get('carbs_per_hour', DEFAULT_CARBS_PER_HOUR))
        water_per_hour = float(data.get('water_per_hour', DEFAULT_WATER_PER_HOUR))
        carbs_per_gel = data.get('carbs_per_gel')  # Optional: carbs per gel/sachet
        if carbs_per_gel is not None and carbs_per_gel != '':
            carbs_per_gel = float(carbs_per_gel)
        else:
            carbs_per_gel = None
        climbing_ability = data.get('climbing_ability', 'moderate')
        race_start_time = data.get('race_start_time')  # "HH:MM" or None
        
        # Fatigue settings
        fatigue_enabled = data.get('fatigue_enabled', True)
        fitness_level = data.get('fitness_level', 'recreational')
        
        # Terrain settings
        skill_level = float(data.get('skill_level', 0.5))  # 0.0 = novice, 1.0 = expert
        
        # Check if elevation profile is provided (from loaded plan)
        elevation_profile_data = data.get('elevation_profile')
        
        if elevation_profile_data:
            # Use provided elevation profile instead of parsing GPX
            # Reconstruct trackpoints from elevation profile for elevation calculations
            trackpoints = []
            for point in elevation_profile_data:
                # Create trackpoints with elevation data
                # Note: lat/lon are dummy values (0.0, 0.0) - only elevation is used
                trackpoints.append((0.0, 0.0, point['elevation']))
            
            # Calculate total distance from the elevation profile
            total_distance = elevation_profile_data[-1]['distance']
            
            # Find checkpoint indices using elevation profile distances
            checkpoint_indices, distances = find_checkpoint_indices_from_profile(elevation_profile_data, checkpoint_distances)
        else:
            # Get uploaded GPX file and parse it
            filename = data.get('gpx_filename')
            if not filename:
                return jsonify({'error': 'No GPX file specified'}), 400
            
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if not os.path.exists(filepath):
                return jsonify({'error': 'GPX file not found'}), 400
            
            # Parse GPX
            trackpoints = parse_gpx_file(filepath)
            total_distance = calculate_total_distance(trackpoints)
            
            # Find checkpoint indices using trackpoints
            checkpoint_indices, distances = find_checkpoint_indices(trackpoints, checkpoint_distances)
        
        # Calculate segments with cumulative effort tracking
        segments = []
        cumulative_time = 0.0
        total_moving_time = 0.0
        cumulative_effort = 0.0  # Track effort in km-effort
        
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
            
            # Get terrain type for this segment (default to 'smooth_trail' if not provided)
            terrain_type = segment_terrain_types[i] if i < len(segment_terrain_types) else 'smooth_trail'
            
            # Calculate pace using cumulative effort (BEFORE adding this segment's effort)
            adjusted_pace, elev_adjusted_pace, fatigue_seconds, terrain_factor, pace_capped = adjust_pace_for_elevation(
                z2_pace, elev_gain, elev_loss, segment_dist, cumulative_effort, climbing_ability,
                fatigue_enabled, fitness_level, terrain_type, skill_level
            )
            
            # Update cumulative effort: effort_km = distance_km + ascent_m/100 + descent_m/200
            segment_effort = segment_dist + (elev_gain / 100.0) + (elev_loss / 200.0)
            cumulative_effort += segment_effort
            
            # Log when pace is capped
            if pace_capped:
                segment_label = f"{segment_labels[i]} → {segment_labels[i + 1]}"
                print(f"⚠️  PACE CAPPED: {segment_label} - Pace limited to {adjusted_pace:.2f} min/km (2.5× base pace)")

            
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
            
            # Calculate terrain penalty percentage for display
            terrain_penalty_pct = (terrain_factor - 1.0) * 100.0
            
            segment_data = {
                'from': segment_labels[i],
                'to': segment_labels[i + 1],
                'distance': round(segment_dist, 2),
                'elev_gain': round(elev_gain, 0),
                'elev_loss': round(elev_loss, 0),
                'net_elev': round(net_elev_change, 0),
                'segment_effort': round(segment_effort, 2),
                'cumulative_effort': round(cumulative_effort, 2),
                'elev_pace': round(elev_adjusted_pace, 2),
                'elev_pace_str': f"{int(elev_adjusted_pace)}:{int((elev_adjusted_pace % 1) * 60):02d}",
                'pace': round(adjusted_pace, 2),
                'pace_str': f"{int(adjusted_pace)}:{int((adjusted_pace % 1) * 60):02d}",
                'pace_capped': pace_capped,
                'fatigue_seconds': round(fatigue_seconds, 1),
                'fatigue_str': f"+{int(fatigue_seconds // 60)}:{int(fatigue_seconds % 60):02d}",
                'terrain_type': terrain_type,
                'terrain_factor': round(terrain_factor, 3),
                'terrain_penalty_pct': round(terrain_penalty_pct, 1),
                'segment_time': round(segment_time, 2),
                'segment_time_str': format_time(segment_time),
                'cumulative_time': round(cumulative_time, 2),
                'cumulative_time_str': format_time(cumulative_time),
                'target_carbs': target_carbs,
                'target_water': target_water_L,
                'time_of_day': time_of_day
            }
            
            if carbs_per_gel and carbs_per_gel > 0:
                segment_data['num_gels'] = round(target_carbs / carbs_per_gel)
            
            segments.append(segment_data)
        
        # Calculate totals
        total_elev_gain = sum(s['elev_gain'] for s in segments)
        total_carbs = sum(s['target_carbs'] for s in segments)
        total_water = sum(s['target_water'] for s in segments)
        total_cp_time = avg_cp_time * num_checkpoints
        
        # Build elevation profile data
        # If elevation profile was provided, keep it; otherwise generate from trackpoints
        if elevation_profile_data:
            # Use the provided elevation profile (already has correct distance values)
            elevation_profile = elevation_profile_data
        else:
            # Generate elevation profile from parsed GPX trackpoints
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
        
        # Calculate dropbag contents
        dropbag_contents = calculate_dropbag_contents(segments, checkpoint_dropbags, carbs_per_gel)
        
        return jsonify({
            'segments': segments,
            'elevation_profile': elevation_profile,
            'dropbag_contents': dropbag_contents,
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
    """Save race plan - supports both Supabase and legacy file-based storage."""
    try:
        data = request.json
        if data is None:
            return jsonify({'error': 'Invalid JSON data'}), 400
        
        plan_name = data.get('plan_name', f"race_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        force_save_as = data.get('force_save_as', False)
        
        # Sanitize plan name
        plan_name = secure_filename(plan_name)
        if plan_name.endswith('.json'):
            plan_name = plan_name[:-5]  # Remove .json extension for database storage
        
        # Prepare plan data
        save_data = {
            'plan_name': data.get('plan_name'),
            'gpx_filename': data.get('gpx_filename'),
            'checkpoint_distances': data.get('checkpoint_distances', []),
            'checkpoint_dropbags': data.get('checkpoint_dropbags', []),
            'segment_terrain_types': data.get('segment_terrain_types', []),
            'avg_cp_time': data.get('avg_cp_time'),
            'z2_pace': data.get('z2_pace'),
            'climbing_ability': data.get('climbing_ability'),
            'carbs_per_hour': data.get('carbs_per_hour'),
            'water_per_hour': data.get('water_per_hour'),
            'carbs_per_gel': data.get('carbs_per_gel'),
            'race_start_time': data.get('race_start_time'),
            'fatigue_enabled': data.get('fatigue_enabled'),
            'fitness_level': data.get('fitness_level'),
            'skill_level': data.get('skill_level'),
            'segments': data.get('segments'),
            'summary': data.get('summary'),
            'elevation_profile': data.get('elevation_profile'),
            'dropbag_contents': data.get('dropbag_contents')
        }
        
        # Try Supabase first if enabled
        if is_supabase_enabled():
            user_info = get_user_id_from_request()
            
            if user_info:
                try:
                    # Determine owner_id or anonymous_id
                    owner_id = user_info['id'] if user_info['type'] == 'authenticated' else None
                    anonymous_id = user_info['id'] if user_info['type'] == 'anonymous' else None
                    
                    # Use admin client for authenticated users (bypasses RLS since we've already validated)
                    # Use regular client for anonymous users (RLS allows anonymous_id based access)
                    client = get_supabase_admin_client() if owner_id else get_supabase_client()
                    if not client:
                        raise Exception("Supabase client not available")
                    
                    # Check if plan exists for this user
                    query = client.table('user_plans').select('id')
                    if owner_id:
                        query = query.eq('owner_id', owner_id)
                    else:
                        query = query.eq('anonymous_id', anonymous_id)
                    query = query.eq('plan_name', plan_name)
                    existing = query.execute()
                    
                    if force_save_as and existing.data:
                        return jsonify({'error': 'A plan with this name already exists. Please choose a different name.'}), 409
                    
                    # Insert or update
                    plan_record = {
                        'owner_id': owner_id,
                        'anonymous_id': anonymous_id,
                        'plan_name': plan_name,
                        'plan_data': save_data
                    }
                    
                    if existing.data and not force_save_as:
                        # Update existing plan
                        result = client.table('user_plans').update({
                            'plan_data': save_data,
                            'updated_at': datetime.now().isoformat()
                        }).eq('id', existing.data[0]['id']).execute()
                    else:
                        # Insert new plan
                        result = client.table('user_plans').insert(plan_record).execute()
                    
                    return jsonify({'message': 'Plan saved successfully', 'filename': f"{plan_name}.json"})
                except Exception as e:
                    print(f"Supabase save error: {e}")
                    # Fall through to file-based storage
        
        # Fall back to file-based storage
        plan_filename = f"{plan_name}.json"
        filepath = os.path.join(app.config['SAVED_PLANS_FOLDER'], plan_filename)
        
        if force_save_as and os.path.exists(filepath):
            return jsonify({'error': 'A plan with this name already exists. Please choose a different name.'}), 409
        
        with open(filepath, 'w') as f:
            json.dump(save_data, f, indent=2)
        
        return jsonify({'message': 'Plan saved successfully', 'filename': plan_filename})
    except Exception as e:
        print(f"Save plan error: {e}")
        return jsonify({'error': str(e)}), 400

@app.route('/api/list-plans', methods=['GET'])
def list_plans():
    """List all saved race plans - supports both Supabase and legacy file-based storage."""
    try:
        # Try Supabase first if enabled
        if is_supabase_enabled():
            user_info = get_user_id_from_request()
            
            if user_info:
                try:
                    # Use admin client for authenticated users, regular client for anonymous
                    client = get_supabase_admin_client() if user_info['type'] == 'authenticated' else get_supabase_client()
                    if not client:
                        raise Exception("Supabase client not available")
                    
                    # Query plans for this user
                    query = client.table('user_plans').select('id, plan_name, created_at, updated_at')
                    
                    if user_info['type'] == 'authenticated':
                        query = query.eq('owner_id', user_info['id'])
                    else:
                        query = query.eq('anonymous_id', user_info['id'])
                    
                    result = query.order('updated_at', desc=True).execute()
                    
                    plans = []
                    for plan in result.data:
                        plans.append({
                            'filename': f"{plan['plan_name']}.json",
                            'name': plan['plan_name'],
                            'modified': plan['updated_at'][:19].replace('T', ' ')  # Format as YYYY-MM-DD HH:MM:SS
                        })
                    
                    return jsonify({'plans': plans})
                except Exception as e:
                    print(f"Supabase list error: {e}")
                    # Fall through to file-based storage
        
        # Fall back to file-based storage
        plans = []
        if os.path.exists(app.config['SAVED_PLANS_FOLDER']):
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
        print(f"List plans error: {e}")
        return jsonify({'error': str(e)}), 400

@app.route('/api/load-plan/<filename>', methods=['GET'])
def load_plan(filename):
    """Load a saved race plan - supports both Supabase and legacy file-based storage."""
    try:
        # Remove .json extension if present for database queries
        plan_name = filename.replace('.json', '')
        
        # Try Supabase first if enabled
        if is_supabase_enabled():
            user_info = get_user_id_from_request()
            
            if user_info:
                try:
                    # Use admin client for authenticated users, regular client for anonymous
                    client = get_supabase_admin_client() if user_info['type'] == 'authenticated' else get_supabase_client()
                    if not client:
                        raise Exception("Supabase client not available")
                    
                    # Query plan for this user
                    query = client.table('user_plans').select('plan_data')
                    
                    if user_info['type'] == 'authenticated':
                        query = query.eq('owner_id', user_info['id'])
                    else:
                        query = query.eq('anonymous_id', user_info['id'])
                    
                    query = query.eq('plan_name', plan_name)
                    result = query.execute()
                    
                    if result.data:
                        return jsonify(result.data[0]['plan_data'])
                    else:
                        # Try file-based storage as fallback
                        pass
                except Exception as e:
                    print(f"Supabase load error: {e}")
                    # Fall through to file-based storage
        
        # Fall back to file-based storage
        filepath = os.path.join(app.config['SAVED_PLANS_FOLDER'], secure_filename(filename))
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'Plan not found'}), 404
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        return jsonify(data)
    except Exception as e:
        print(f"Load plan error: {e}")
        return jsonify({'error': str(e)}), 400

@app.route('/api/delete-plan/<filename>', methods=['DELETE'])
def delete_plan(filename):
    """Delete a saved race plan - supports both Supabase and legacy file-based storage."""
    try:
        # Remove .json extension if present for database queries
        plan_name = filename.replace('.json', '')
        
        # Try Supabase first if enabled
        if is_supabase_enabled():
            user_info = get_user_id_from_request()
            
            if user_info:
                try:
                    # Use admin client for authenticated users, regular client for anonymous
                    client = get_supabase_admin_client() if user_info['type'] == 'authenticated' else get_supabase_client()
                    if not client:
                        raise Exception("Supabase client not available")
                    
                    # Delete plan for this user
                    query = client.table('user_plans').delete()
                    
                    if user_info['type'] == 'authenticated':
                        query = query.eq('owner_id', user_info['id'])
                    else:
                        query = query.eq('anonymous_id', user_info['id'])
                    
                    query = query.eq('plan_name', plan_name)
                    result = query.execute()
                    
                    if result.data:
                        return jsonify({'message': 'Plan deleted successfully'})
                    else:
                        # Try file-based storage as fallback
                        pass
                except Exception as e:
                    print(f"Supabase delete error: {e}")
                    # Fall through to file-based storage
        
        # Fall back to file-based storage
        filepath = os.path.join(app.config['SAVED_PLANS_FOLDER'], secure_filename(filename))
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'Plan not found'}), 404
        
        os.remove(filepath)
        return jsonify({'message': 'Plan deleted successfully'})
    except Exception as e:
        print(f"Delete plan error: {e}")
        return jsonify({'error': str(e)}), 400

@app.route('/api/export-plan', methods=['POST'])
def export_plan():
    """Export current race plan as a JSON file."""
    try:
        data = request.json
        if data is None:
            return jsonify({'error': 'Invalid JSON data'}), 400
        
        # Return the plan data as-is, with export metadata
        return jsonify({
            'version': '1.0',
            'export_date': datetime.now().isoformat(),
            'plan': data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/import-plan', methods=['POST'])
def import_plan():
    """Import a single plan from JSON file."""
    try:
        data = request.json
        if data is None:
            return jsonify({'error': 'Invalid JSON data'}), 400
        
        # Validate structure - expecting either the old format with 'plans' key
        # or new format with 'plan' key, or just the plan data directly
        plan_data = None
        
        if 'plan' in data:
            # New format
            plan_data = data['plan']
        elif 'plans' in data and isinstance(data['plans'], dict):
            # Old format - take the first plan
            plans = data['plans']
            if len(plans) > 0:
                plan_data = list(plans.values())[0]
        else:
            # Assume the entire data is the plan
            plan_data = data
        
        if plan_data is None or not isinstance(plan_data, dict):
            return jsonify({'error': 'Invalid format: unable to find valid plan data'}), 400
        
        # Return the plan data so the frontend can load it
        return jsonify({
            'message': 'Plan imported successfully',
            'plan': plan_data
        })
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
        dropbag_contents = data.get('dropbag_contents', [])
        
        # Generate CSV in memory
        csv_filename = f"race_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        header = ['Segment', 'Distance (km)', 'Elev Gain (m)', 'Elev Loss (m)', 'Net Elev (m)', 
                 'Elev Pace (min/km)', 'Fatigue (mm:ss)', 'Terrain Type', 'Terrain Factor', 'Final Pace (min/km)', 
                 'Segment Time', 'Carbs (g)', 'Water (L)', 'Cumulative Time']
        if race_start_time:
            header.append('Time of Arrival at CP')
        writer.writerow(header)
        
        # Data rows
        for seg in segments:
            # Extract checkpoint name from segment 'to' field for dynamic column naming
            checkpoint_name = seg['to']
            row = [
                f"{seg['from']} to {seg['to']}",
                seg['distance'],
                seg['elev_gain'],
                seg['elev_loss'],
                seg['net_elev'],
                seg['elev_pace_str'],
                seg['fatigue_str'],
                seg.get('terrain_type', 'smooth_trail'),
                seg.get('terrain_factor', 1.0),
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
        
        # Dropbag contents
        if dropbag_contents and len(dropbag_contents) > 0:
            writer.writerow([])
            writer.writerow(['DROP BAG CONTENTS'])
            
            # Check if gel data is present
            has_gel_data = any('num_gels' in dropbag for dropbag in dropbag_contents)
            
            if has_gel_data:
                writer.writerow(['Checkpoint', 'Carb Target (g)', 'Number of Gels', 'Actual Carbs (g)', 'Hydration Target (L)'])
                for dropbag in dropbag_contents:
                    writer.writerow([
                        dropbag['checkpoint'], 
                        dropbag['carbs'], 
                        dropbag.get('num_gels', ''),
                        dropbag.get('actual_carbs', ''),
                        dropbag['hydration']
                    ])
            else:
                writer.writerow(['Checkpoint', 'Carb Target (g)', 'Hydration Target (L)'])
                for dropbag in dropbag_contents:
                    writer.writerow([dropbag['checkpoint'], dropbag['carbs'], dropbag['hydration']])
        
        csv_content = output.getvalue()
        output.close()
        
        return send_file(io.BytesIO(csv_content.encode('utf-8')), 
                        as_attachment=True, 
                        download_name=csv_filename, 
                        mimetype='text/csv')
    except Exception as e:
        return jsonify({'error': str(e)}), 400


# Authentication Endpoints

@app.route('/api/auth/check', methods=['GET'])
def check_auth():
    """Check if Supabase authentication is enabled and get current user status."""
    return jsonify({
        'supabase_enabled': is_supabase_enabled(),
        'supabase_url': SUPABASE_URL if is_supabase_enabled() else None,
        'supabase_anon_key': SUPABASE_ANON_KEY if is_supabase_enabled() else None
    })


@app.route('/api/auth/list-anonymous-plans', methods=['POST'])
def list_anonymous_plans():
    """List all plans for a given anonymous ID."""
    if not is_supabase_enabled():
        return jsonify({'error': 'Supabase is not configured'}), 400
    
    try:
        data = request.json
        anonymous_id = data.get('anonymous_id')
        
        if not anonymous_id:
            return jsonify({'error': 'Anonymous ID required'}), 400
        
        # Query plans for this anonymous ID - use admin client to bypass RLS
        admin_client = get_supabase_admin_client()
        if not admin_client:
            return jsonify({'error': 'Database service not available'}), 500
        
        result = admin_client.table('user_plans').select('id, plan_name, created_at, updated_at').eq('anonymous_id', anonymous_id).order('updated_at', desc=True).execute()
        
        plans = []
        for plan in result.data:
            plans.append({
                'id': plan['id'],
                'name': plan['plan_name'],
                'created_at': plan['created_at'][:19].replace('T', ' '),
                'updated_at': plan['updated_at'][:19].replace('T', ' ')
            })
        
        return jsonify({'plans': plans})
    except Exception as e:
        print(f"List anonymous plans error: {e}")
        return jsonify({'error': str(e)}), 400


@app.route('/api/auth/migrate', methods=['POST'])
def migrate_anonymous_data():
    """Migrate selected anonymous plans to authenticated user account."""
    if not is_supabase_enabled():
        return jsonify({'error': 'Supabase is not configured'}), 400
    
    try:
        data = request.json
        auth_header = request.headers.get('Authorization')
        anonymous_id = data.get('anonymous_id')
        plan_ids = data.get('plan_ids', [])  # List of plan IDs to migrate
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authorization header required'}), 401
        
        if not anonymous_id:
            return jsonify({'error': 'Anonymous ID required'}), 400
        
        # Get authenticated user
        token = auth_header.replace('Bearer ', '')
        user = get_supabase_client().auth.get_user(token)
        
        if not user or not hasattr(user, 'user') or not user.user:
            return jsonify({'error': 'Invalid authentication token'}), 401
        
        user_id = user.user.id
        
        # If no plan_ids provided, don't migrate anything (user chose to skip)
        if not plan_ids:
            return jsonify({
                'message': 'No plans migrated',
                'migrated_plans': 0
            })
        
        # Call the migration function in Supabase with selected plan IDs
        admin_client = get_supabase_admin_client()
        if admin_client:
            result = admin_client.rpc(
                'migrate_selected_anonymous_plans',
                {'p_anonymous_id': anonymous_id, 'p_user_id': user_id, 'p_plan_ids': plan_ids}
            ).execute()
            
            migrated_count = result.data if result.data else 0
            
            return jsonify({
                'message': 'Migration completed successfully',
                'migrated_plans': migrated_count
            })
        else:
            return jsonify({'error': 'Migration service not available'}), 500
            
    except Exception as e:
        print(f"Migration error: {e}")
        return jsonify({'error': f'Migration failed: {str(e)}'}), 500


if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', '0').lower() in ('1', 'true')
    app.run(host='0.0.0.0', port=5001, debug=debug_mode)
