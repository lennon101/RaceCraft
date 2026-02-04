"""
RaceCraft - Fuel & Pacing Planner
Version: v1.5.3
Release Date: Feb 02, 2026

Major Changes in v1.5.3:
- Move all docs to folder and organise 
- Update Readme with new links

Major Changes in v1.5.0-load-known-races:
- Display loaded plan name in UI title #64 
- Clear form inputs and state on user sign-out #60 
- Add manual import for local and unowned plans #59 
- Support anonymous user plans in list/load/delete endpoints #56 

Major Changes in v1.4.1:
- Fix Supabase client initialization to be lazy and handle invalid credentials gracefully
- Improved logging for authentication processes
- Input fields now cleared on gpx load or user sign-out to prevent stale data issues

Major Changes in v1.4.0:
- Supabase Integration for User Authentication and Data Storage

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
import sys
import xml.etree.ElementTree as ET
import math
import io
import csv
from datetime import datetime, timezone
from werkzeug.utils import secure_filename
import json
import os
import platform
from functools import wraps
from dotenv import load_dotenv
from whitenoise import WhiteNoise

# Load environment variables
load_dotenv()

# Helper function for logging that ensures output is visible in Railway/gunicorn
def log_message(message):
    """Print message and immediately flush to ensure it appears in logs."""
    print(message)
    sys.stdout.flush()

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
        
        # Check service key for authenticated user support
        if SUPABASE_SERVICE_KEY:
            service_key_preview = SUPABASE_SERVICE_KEY[:20] + "..." if len(SUPABASE_SERVICE_KEY) > 20 else SUPABASE_SERVICE_KEY
            print(f"  Service key: {service_key_preview}")
            print("  ✓ Authenticated user database operations enabled")
        else:
            print("  ⚠ WARNING: SUPABASE_SERVICE_KEY not set!")
            print("  ⚠ Authenticated users will NOT be able to save plans to database")
            print("  ⚠ Set SUPABASE_SERVICE_KEY environment variable to fix this")
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
    # Known races are in a static location not affected by volume mounts
    app.config['KNOWN_RACES_FOLDER'] = '/app/static_data/known_races'
else:
    # Local development environment
    app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'FuelPlanData', 'uploads')
    app.config['SAVED_PLANS_FOLDER'] = os.path.join(os.getcwd(), 'FuelPlanData', 'saved_plans')
    # For local dev, check both data/ (source of truth) and FuelPlanData/ (legacy)
    if os.path.exists(os.path.join(os.getcwd(), 'data', 'known_races')):
        app.config['KNOWN_RACES_FOLDER'] = os.path.join(os.getcwd(), 'data', 'known_races')
    else:
        app.config['KNOWN_RACES_FOLDER'] = os.path.join(os.getcwd(), 'FuelPlanData', 'known_races')

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['SAVED_PLANS_FOLDER'], exist_ok=True)
os.makedirs(app.config['KNOWN_RACES_FOLDER'], exist_ok=True)

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
        log_message(f"   Invalid auth header format")
        return None
    
    # Get the client (creates it lazily if needed)
    client = get_supabase_client()
    if not client:
        log_message(f"   Failed to get supabase client")
        return None
    
    try:
        token = auth_header.replace('Bearer ', '')
        log_message(f"   Validating token (length: {len(token)})")
        user = client.auth.get_user(token)
        log_message(f"   Token validation successful: {bool(user)}")
        if user:
            log_message(f"   User object has .user attribute: {hasattr(user, 'user')}")
            if hasattr(user, 'user'):
                log_message(f"   user.user value: {user.user}")
        return user
    except Exception as e:
        log_message(f"   ❌ Error validating token: {e}")
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        return None


def get_user_id_from_request():
    """Get user ID from request, supporting both authenticated and anonymous users."""
    auth_header = request.headers.get('Authorization')
    log_message(f"🔐 get_user_id_from_request called")
    log_message(f"   Authorization header present: {bool(auth_header)}")
    log_message(f"   Authorization header value: {auth_header[:50] if auth_header else 'None'}...")
    
    # Try to get authenticated user
    if auth_header:
        # Get the client (creates it lazily if needed)
        client = get_supabase_client()
        if client:
            log_message(f"   Attempting to validate token...")
            user = get_user_from_token(auth_header)
            log_message(f"   Token validation result: {user}")
            if user and hasattr(user, 'user') and user.user:
                log_message(f"   ✓ Authenticated user found: {user.user.id}")
                return {'type': 'authenticated', 'id': user.user.id}
            else:
                log_message(f"   ❌ Token validation failed or returned no user")
        else:
            log_message(f"   ⚠️ supabase_client could not be created")
    else:
        log_message(f"   ⚠️ No Authorization header in request")
    
    # Fall back to anonymous ID from request
    anonymous_id = request.headers.get('X-Anonymous-ID')
    log_message(f"   X-Anonymous-ID header: {anonymous_id}")
    if anonymous_id:
        log_message(f"   Using anonymous ID: {anonymous_id}")
        return {'type': 'anonymous', 'id': anonymous_id}
    
    log_message(f"   ❌ No user identification found - returning None")
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
            print(f"Attempting to create Supabase anon client with URL: {SUPABASE_URL}")
            supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
            print("✓ Supabase anon client created successfully")
        except Exception as e:
            print(f"❌ Failed to create Supabase client: {e}")
            import traceback
            traceback.print_exc()
            return None
    return supabase_client

def get_supabase_admin_client():
    """Get or create the Supabase admin client."""
    global supabase_admin_client
    if supabase_admin_client is None and is_supabase_enabled() and supabase_import_available and SUPABASE_SERVICE_KEY:
        try:
            from supabase import create_client
            print(f"Attempting to create Supabase admin client with URL: {SUPABASE_URL}")
            supabase_admin_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
            print("✓ Supabase admin client created successfully")
        except Exception as e:
            print(f"❌ Failed to create Supabase admin client: {e}")
            import traceback
            traceback.print_exc()
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

def parse_known_race_filename(filename):
    """
    Parse known race filename according to format: Organiser-race_name-year.gpx
    Returns dict with organiser, race_name, year, or None if invalid format.
    """
    if not filename.endswith('.gpx'):
        return None
    
    # Remove .gpx extension
    name_without_ext = filename[:-4]
    
    # Split by '-' and expect at least 3 parts
    parts = name_without_ext.split('-')
    if len(parts) < 3:
        return None
    
    # Last part should be a 4-digit year
    year_str = parts[-1]
    if not (year_str.isdigit() and len(year_str) == 4):
        return None
    
    # First part is organiser, everything in between is race name
    organiser = parts[0]
    race_name = '-'.join(parts[1:-1])  # Join middle parts back together
    year = int(year_str)
    
    return {
        'organiser': organiser,
        'race_name': race_name.replace('_', ' '),  # Convert underscores to spaces
        'year': year,
        'filename': filename
    }

@app.route('/api/list-known-races', methods=['GET'])
def list_known_races():
    """List all known races from the known_races directory."""
    try:
        known_races_folder = app.config['KNOWN_RACES_FOLDER']
        
        if not os.path.exists(known_races_folder):
            return jsonify({'races': [], 'error': 'Known races folder not found'})
        
        races = []
        for filename in os.listdir(known_races_folder):
            if filename.endswith('.gpx'):
                parsed = parse_known_race_filename(filename)
                if parsed:
                    # Add full path for internal use
                    parsed['filepath'] = os.path.join(known_races_folder, filename)
                    races.append(parsed)
        
        # Sort by year (descending), then by organiser, then by race name
        races.sort(key=lambda x: (-x['year'], x['organiser'], x['race_name']))
        
        # Group by organiser
        grouped = {}
        for race in races:
            organiser = race['organiser']
            if organiser not in grouped:
                grouped[organiser] = []
            grouped[organiser].append(race)
        
        return jsonify({
            'races': races,
            'grouped': grouped
        })
    except Exception as e:
        return jsonify({'error': f'Error listing known races: {str(e)}'}), 500

@app.route('/api/load-known-race/<filename>', methods=['GET'])
def load_known_race(filename):
    """Load a known race GPX file."""
    try:
        from werkzeug.utils import secure_filename
        secure_name = secure_filename(filename)
        filepath = os.path.join(app.config['KNOWN_RACES_FOLDER'], secure_name)
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'Known race file not found'}), 404
        
        # Parse the GPX file
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
        
        # Parse metadata from filename
        metadata = parse_known_race_filename(filename)
        
        return jsonify({
            'filename': secure_name,
            'total_distance': round(total_distance, 2),
            'total_distance_miles': round(total_distance * 0.621371, 2),
            'total_elev_gain': round(total_elev_gain, 0),
            'total_elev_loss': round(total_elev_loss, 0),
            'num_trackpoints': len(trackpoints),
            'metadata': metadata,
            'is_known_race': True
        })
    except Exception as e:
        return jsonify({'error': f'Error loading known race: {str(e)}'}), 500

def calculate_natural_pacing(segments_data, base_pace, climbing_ability='moderate',
                            fatigue_enabled=True, fitness_level='recreational',
                            skill_level=0.5):
    """
    Calculate what the athlete would naturally do "on autopilot" (forward model).
    
    This is the prediction model: ability → pace → finish time
    
    Args:
        segments_data: List of dicts with 'distance', 'elev_gain', 'elev_loss', 'terrain_type'
        base_pace: Flat pace in min/km
        climbing_ability: Athlete climbing ability
        fatigue_enabled: Whether to apply fatigue
        fitness_level: Athlete fitness level
        skill_level: Technical skill (0.0-1.0)
    
    Returns:
        List of dicts with 'natural_time' (minutes), 'natural_pace' (min/km) for each segment
    """
    results = []
    cumulative_effort = 0.0
    
    log_message(f"Computing natural pacing for {climbing_ability} climber")
    
    for i, seg_data in enumerate(segments_data):
        distance_km = seg_data['distance']
        elev_gain = seg_data['elev_gain']
        elev_loss = seg_data['elev_loss']
        terrain_type = seg_data.get('terrain_type', 'smooth_trail')
        
        # Use athlete's actual ability to predict natural pace
        natural_pace, _, _, _, _ = adjust_pace_for_elevation(
            base_pace, elev_gain, elev_loss, distance_km, cumulative_effort,
            climbing_ability, fatigue_enabled, fitness_level, terrain_type, skill_level
        )
        
        natural_time = natural_pace * distance_km
        
        results.append({
            'natural_time': natural_time,
            'natural_pace': natural_pace
        })
        
        log_message(f"  Segment {i}: natural pace = {natural_pace:.2f} min/km, time = {natural_time:.2f} min")
        
        # Update cumulative effort for next segment
        segment_effort = distance_km + (elev_gain / 100.0) + (elev_loss / 200.0)
        cumulative_effort += segment_effort
    
    total_natural_time = sum(r['natural_time'] for r in results)
    log_message(f"Total natural time: {total_natural_time:.2f} min")
    
    return results


def get_terrain_effort_bounds(elev_gain, elev_loss, distance_km, climbing_ability, skill_level):
    """
    Define how much a segment's pace can be adjusted based on terrain type and athlete ability.
    
    This is where abilities affect COST, CAPACITY, and LIMITS.
    
    Returns: (min_multiplier, max_multiplier, effort_cost_multiplier)
    - min_multiplier < 1.0: can speed up
    - max_multiplier > 1.0: can slow down
    - effort_cost_multiplier: how "expensive" it is to buy time here (lower = cheaper)
    
    Abilities affect:
    - Climbing ability: cost of buying time on climbs (elite = cheaper)
    - Technical skill: cost and limits on descents (high skill = less expensive, still constrained)
    - Bounds: already implemented (capacity limits)
    """
    gradient = (elev_gain - elev_loss) / (distance_km * 1000.0) if distance_km > 0 else 0.0
    
    # Climbing ability cost multipliers (lower = cheaper to buy time)
    climbing_cost_map = {
        'elite': 0.75,         # Climbs are very cheap for elite
        'very_strong': 0.85,
        'strong': 0.95,
        'moderate': 1.0,       # Baseline
        'conservative': 1.2    # Climbs are expensive for conservative
    }
    climbing_cost = climbing_cost_map.get(climbing_ability, 1.0)
    
    # Technical skill affects downhill cost (0.0 = novice, 1.0 = expert)
    # Even experts pay a cost on descents (safety/risk factor)
    skill_cost_factor = 1.0 + (1.0 - skill_level) * 0.8  # Range: 1.0 (expert) to 1.8 (novice)
    
    # Classify terrain by gradient
    if gradient > 0.08:  # Steep climb (>8%)
        # Climbing is where ability matters most
        # Cost is heavily affected by climbing ability
        effort_cost = climbing_cost
        
        if climbing_ability == 'elite':
            return (0.70, 1.15, effort_cost)  # Can push much harder, less slowdown
        elif climbing_ability == 'very_strong':
            return (0.75, 1.20, effort_cost)
        elif climbing_ability == 'strong':
            return (0.80, 1.25, effort_cost)
        elif climbing_ability == 'moderate':
            return (0.85, 1.30, effort_cost)
        else:  # conservative
            return (0.90, 1.35, effort_cost)  # Limited improvement, more slowdown
    
    elif gradient < -0.05:  # Descent (< -5%)
        # Descents are constrained by technical skill
        # Cost affected by skill level (risk pricing)
        effort_cost = skill_cost_factor
        
        # Hard caps on descents - even skilled athletes have limits
        if skill_level >= 0.8:  # Expert (0.8-1.0)
            return (0.80, 1.20, effort_cost)  # Moderate adjustment, still constrained
        elif skill_level >= 0.6:  # Proficient (0.6-0.8)
            return (0.85, 1.20, effort_cost)  # Less speed-up range
        elif skill_level >= 0.4:  # Intermediate (0.4-0.6)
            return (0.90, 1.25, effort_cost)  # Limited speed-up
        else:  # Novice (0.0-0.4)
            return (0.95, 1.30, effort_cost)  # Very limited, expensive
    
    else:  # Flat or rolling (between -5% and +8%)
        # Medium adjustment range, less ability-dependent
        # Baseline cost (not affected much by abilities)
        effort_cost = 1.0
        return (0.80, 1.25, effort_cost)


def allocate_effort_to_target(target_time_minutes, segments_data, natural_results, 
                               base_pace, climbing_ability, fatigue_enabled,
                               fitness_level, skill_level):
    """
    Effort allocation optimizer for target time mode.
    
    This is constrained optimization, NOT pace inversion.
    
    Strategy:
    1. Start with natural pacing (what athlete would do on autopilot)
    2. Calculate ΔT = T_natural - T_target
    3. Calculate effort costs for each segment (climbing ability, technical skill)
    4. Apply global effort budget (fitness level)
    5. Distribute ΔT prioritizing lowest-cost segments
    6. Apply cumulative fatigue multiplier (prefer early effort)
    
    Abilities affect COST, CAPACITY, and LIMITS:
    - Climbing ability: climbs cheaper for elite (cost multiplier)
    - Technical skill: descents expensive for novice (risk pricing)
    - Fitness level: total deviation budget (global constraint)
    
    Args:
        target_time_minutes: Target total moving time
        segments_data: Segment info (distance, elevation, terrain)
        natural_results: Natural pacing from calculate_natural_pacing()
        base_pace: Flat terrain pace
        climbing_ability: Athlete ability level
        fatigue_enabled: Whether fatigue is enabled
        fitness_level: Athlete fitness level
        skill_level: Technical skill level (0.0-1.0)
    
    Returns:
        List of dicts with 'segment_time', 'required_pace', 'effort_level' for each segment
    """
    if not natural_results:
        return []
    
    natural_total_time = sum(r['natural_time'] for r in natural_results)
    delta_t = natural_total_time - target_time_minutes
    
    log_message(f"Effort allocation: natural={natural_total_time:.2f} min, target={target_time_minutes:.2f} min, ΔT={delta_t:.2f} min")
    
    # If target matches natural, no adjustment needed
    if abs(delta_t) < 0.5:  # Within 30 seconds
        results = []
        for i, seg_data in enumerate(segments_data):
            results.append({
                'segment_time': natural_results[i]['natural_time'],
                'required_pace': natural_results[i]['natural_pace'],
                'effort_level': 'steady'
            })
        return results
    
    # Fitness-based global effort budget (how much total deviation is allowed)
    fitness_budget_map = {
        'untrained': 0.15,      # Can only deviate 15% from natural
        'recreational': 0.25,   # 25% deviation
        'trained': 0.35,        # 35% deviation
        'elite': 0.50          # 50% deviation
    }
    global_effort_budget = fitness_budget_map.get(fitness_level, 0.25)
    max_total_deviation = natural_total_time * global_effort_budget
    
    log_message(f"Fitness level: {fitness_level}, global budget: {global_effort_budget:.1%} = {max_total_deviation:.2f} min")
    
    # Calculate how much each segment can contribute with cost weighting
    segment_adjustments = []
    cumulative_effort_km = 0.0
    
    for i, seg_data in enumerate(segments_data):
        distance_km = seg_data['distance']
        elev_gain = seg_data['elev_gain']
        elev_loss = seg_data['elev_loss']
        natural_time = natural_results[i]['natural_time']
        natural_pace = natural_results[i]['natural_pace']
        
        # Get terrain-specific bounds and effort cost
        min_mult, max_mult, base_effort_cost = get_terrain_effort_bounds(
            elev_gain, elev_loss, distance_km, climbing_ability, skill_level
        )
        
        # Apply fatigue multiplier if enabled (cost increases with cumulative effort)
        if fatigue_enabled:
            # Fatigue makes later segments more expensive
            # Fitness affects how steep the cost curve is
            fitness_fatigue_map = {
                'untrained': 1.5,
                'recreational': 1.3,
                'trained': 1.15,
                'elite': 1.05
            }
            fatigue_factor = fitness_fatigue_map.get(fitness_level, 1.3)
            
            # Calculate cumulative effort (km-effort: distance + ascent/100 + descent/200)
            segment_effort = distance_km + (elev_gain / 100.0) + (elev_loss / 200.0)
            
            # Fatigue multiplier grows with cumulative effort
            # Early segments: ~1.0, late segments: up to fatigue_factor
            fatigue_multiplier = 1.0 + (cumulative_effort_km / 100.0) * (fatigue_factor - 1.0)
            fatigue_multiplier = min(fatigue_multiplier, fatigue_factor)  # Cap at fatigue_factor
            
            cumulative_effort_km += segment_effort
        else:
            fatigue_multiplier = 1.0
        
        # Total effort cost = base_cost × fatigue_multiplier
        total_effort_cost = base_effort_cost * fatigue_multiplier
        
        # Calculate time adjustment range with cost
        if delta_t > 0:  # Need to go faster
            # Can reduce time by speeding up (min_mult < 1.0)
            max_time_saved = natural_time * (1.0 - min_mult)
            segment_adjustments.append({
                'index': i,
                'max_adjustment': max_time_saved,
                'effort_cost': total_effort_cost,
                'multiplier': min_mult,
                'direction': 'faster'
            })
        else:  # Need to go slower
            # Can add time by slowing down (max_mult > 1.0)
            max_time_added = natural_time * (max_mult - 1.0)
            segment_adjustments.append({
                'index': i,
                'max_adjustment': max_time_added,
                'effort_cost': total_effort_cost,
                'multiplier': max_mult,
                'direction': 'slower'
            })
    
    # Calculate total capacity
    total_capacity = sum(adj['max_adjustment'] for adj in segment_adjustments)
    
    if total_capacity == 0:
        log_message("Warning: Zero adjustment capacity - using natural pacing")
        results = []
        for i, seg_data in enumerate(segments_data):
            results.append({
                'segment_time': natural_results[i]['natural_time'],
                'required_pace': natural_results[i]['natural_pace'],
                'effort_level': 'steady'
            })
        return results
    
    # Check if target is achievable within global effort budget
    abs_delta_t = abs(delta_t)
    if abs_delta_t > max_total_deviation:
        log_message(f"Warning: Target requires {abs_delta_t:.2f} min deviation, but budget is {max_total_deviation:.2f} min")
        log_message(f"Target time is too aggressive for {fitness_level} fitness level - using maximum feasible effort")
        # Cap delta_t to budget
        abs_delta_t = max_total_deviation
    
    # Distribute delta_t using cost-weighted allocation
    # Lower cost segments get prioritized for adjustment
    results = []
    total_cost_weighted_capacity = sum(adj['max_adjustment'] / adj['effort_cost'] for adj in segment_adjustments)
    
    log_message(f"DEBUG: total_cost_weighted_capacity={total_cost_weighted_capacity:.2f}")
    log_message(f"DEBUG: abs_delta_t after budget cap={abs_delta_t:.2f} min")
    
    for i, seg_data in enumerate(segments_data):
        natural_time = natural_results[i]['natural_time']
        natural_pace = natural_results[i]['natural_pace']
        adj = segment_adjustments[i]
        distance_km = seg_data['distance']
        
        # Calculate this segment's share based on cost-weighted capacity
        # Lower cost = gets more of the adjustment (more efficient use of effort)
        if total_cost_weighted_capacity > 0:
            cost_weighted_share = (adj['max_adjustment'] / adj['effort_cost']) / total_cost_weighted_capacity
            segment_adjustment = cost_weighted_share * abs_delta_t
            
            # Respect segment's max capacity
            segment_adjustment = min(segment_adjustment, adj['max_adjustment'])
        else:
            segment_adjustment = 0
        
        adjustment_pct = (segment_adjustment / natural_time * 100) if natural_time > 0 else 0
        
        # Apply adjustment
        if delta_t > 0:  # Going faster (natural > target, need to speed up)
            adjusted_time = natural_time - segment_adjustment
            effort_level = 'push' if segment_adjustment / natural_time >= 0.10 else 'steady'
            log_message(f"DEBUG seg{i}: delta_t>0 (faster), natural={natural_time:.2f}, adj={segment_adjustment:.2f} ({adjustment_pct:.1f}%), effort={effort_level}")
        else:  # Going slower (natural < target, need to slow down)
            adjusted_time = natural_time + segment_adjustment
            effort_level = 'protect' if segment_adjustment / natural_time >= 0.10 else 'steady'
            log_message(f"DEBUG seg{i}: delta_t<0 (slower), natural={natural_time:.2f}, adj={segment_adjustment:.2f} ({adjustment_pct:.1f}%), effort={effort_level}")
        
        adjusted_pace = adjusted_time / distance_km if distance_km > 0 else natural_pace
        
        results.append({
            'segment_time': adjusted_time,
            'required_pace': adjusted_pace,
            'effort_level': effort_level
        })
        
        log_message(f"  Segment {i}: {effort_level} - pace {adjusted_pace:.2f} min/km (natural: {natural_pace:.2f}, cost: {adj['effort_cost']:.2f})")
    
    return results


def calculate_effort_thresholds(natural_results, segments_data, base_pace, climbing_ability,
                                fatigue_enabled, fitness_level, skill_level, num_checkpoints, avg_cp_time):
    """
    Calculate target time thresholds where effort levels transition.
    
    Simulates the actual allocation logic to find target times where at least one
    segment reaches the 10% adjustment threshold for effort labeling.
    
    Args:
        num_checkpoints: Number of checkpoints (includes finish but not start)
        avg_cp_time: Average time spent at each checkpoint in minutes
    
    Returns:
        dict with 'natural_time', 'push_threshold', 'protect_threshold' in minutes
        (all values include checkpoint time for total race time)
    """
    if not natural_results:
        return None
    
    natural_total_time = sum(r['natural_time'] for r in natural_results)
    
    # Validate natural_total_time to prevent NaN
    if natural_total_time <= 0 or not isinstance(natural_total_time, (int, float)):
        print(f"ERROR: Invalid natural_total_time: {natural_total_time}")
        return None
    
    # Validate inputs to prevent NaN
    if num_checkpoints is None:
        num_checkpoints = 0
    if avg_cp_time is None:
        avg_cp_time = 0
    
    # Calculate total checkpoint time (checkpoint after each segment except first)
    total_cp_time = num_checkpoints * avg_cp_time
    
    print(f"DEBUG threshold calc: natural={natural_total_time}, cp_time={total_cp_time}, num_cp={num_checkpoints}, avg={avg_cp_time}")
    
    def simulate_push_segments(target_time_minutes):
        """
        Simulate allocation for PUSH threshold (going faster).
        Returns percentage of segments that would get "push" labels.
        
        Returns:
            float: Percentage of segments (0.0 to 1.0) that have >=10% faster adjustment
        """
        delta_t = natural_total_time - target_time_minutes
        if delta_t <= 0:  # Not going faster, can't have push labels
            return 0.0
        
        abs_delta_t = abs(delta_t)
        
        # Apply global fitness budget constraint (CRITICAL: matches allocate_effort_to_target)
        fitness_budgets = {'untrained': 0.15, 'recreational': 0.25, 'trained': 0.35, 'elite': 0.50}
        fitness_budget = fitness_budgets.get(fitness_level, 0.25)
        max_total_deviation = natural_total_time * fitness_budget
        
        # Cap delta_t to budget
        if abs_delta_t > max_total_deviation:
            abs_delta_t = max_total_deviation
        
        # Build adjustment data (simplified version of allocate_effort_to_target)
        adjustments = []
        total_weighted_capacity = 0.0
        
        for i, seg_data in enumerate(segments_data):
            distance_km = seg_data['distance']
            elev_gain = seg_data['elev_gain']
            elev_loss = seg_data['elev_loss']
            natural_time = natural_results[i]['natural_time']
            
            # Get bounds and cost
            min_mult, max_mult, base_effort_cost = get_terrain_effort_bounds(
                elev_gain, elev_loss, distance_km, climbing_ability, skill_level
            )
            
            # Capacity for adjustment (only faster direction for push)
            capacity = natural_time * (1.0 - min_mult)
            
            # Total cost (MUST match real allocation - includes cumulative fatigue)
            cumulative_effort_km = sum(
                s['distance'] + (s['elev_gain'] / 100.0) + (s['elev_loss'] / 200.0)
                for s in segments_data[:i]
            )
            
            if fatigue_enabled:
                fitness_fatigue_map = {'untrained': 1.5, 'recreational': 1.3, 'trained': 1.15, 'elite': 1.05}
                fatigue_factor = fitness_fatigue_map.get(fitness_level, 1.3)
                
                # Calculate segment effort
                segment_effort = distance_km + (elev_gain / 100.0) + (elev_loss / 200.0)
                
                # Fatigue multiplier grows with cumulative effort
                fatigue_multiplier = 1.0 + (cumulative_effort_km / 100.0) * (fatigue_factor - 1.0)
                fatigue_multiplier = min(fatigue_multiplier, fatigue_factor)
            else:
                fatigue_multiplier = 1.0
            
            total_cost = base_effort_cost * fatigue_multiplier
            
            adjustments.append({
                'natural_time': natural_time,
                'capacity': capacity,
                'total_cost': total_cost,
                'index': i
            })
            
            if total_cost > 0 and capacity > 0:
                total_weighted_capacity += capacity / total_cost
        
        if total_weighted_capacity == 0:
            return 0.0
        
        # Allocate time based on cost weighting and count segments that hit >= 10%
        segments_at_threshold = 0
        total_segments = len(adjustments)
        
        for adj in adjustments:
            if adj['total_cost'] > 0 and adj['capacity'] > 0:
                weighted_share = (adj['capacity'] / adj['total_cost']) / total_weighted_capacity
                segment_adjustment = min(abs_delta_t * weighted_share, adj['capacity'])
                adjustment_ratio = segment_adjustment / adj['natural_time']
                
                # Only count if going faster AND >=10% adjustment
                if adjustment_ratio >= 0.10:
                    segments_at_threshold += 1
        
        # Return percentage of segments at threshold
        return segments_at_threshold / total_segments if total_segments > 0 else 0.0
    
    def simulate_protect_segments(target_time_minutes):
        """
        Simulate allocation for PROTECT threshold (going slower).
        Returns percentage of segments that would get "protect" labels.
        
        Returns:
            float: Percentage of segments (0.0 to 1.0) that have >=10% slower adjustment
        """
        delta_t = natural_total_time - target_time_minutes
        if delta_t >= 0:  # Not going slower, can't have protect labels
            return 0.0
        
        abs_delta_t = abs(delta_t)
        
        # Apply global fitness budget constraint (CRITICAL: matches allocate_effort_to_target)
        fitness_budgets = {'untrained': 0.15, 'recreational': 0.25, 'trained': 0.35, 'elite': 0.50}
        fitness_budget = fitness_budgets.get(fitness_level, 0.25)
        max_total_deviation = natural_total_time * fitness_budget
        
        # Cap delta_t to budget
        if abs_delta_t > max_total_deviation:
            abs_delta_t = max_total_deviation
        
        # Build adjustment data (simplified version of allocate_effort_to_target)
        adjustments = []
        total_weighted_capacity = 0.0
        
        for i, seg_data in enumerate(segments_data):
            distance_km = seg_data['distance']
            elev_gain = seg_data['elev_gain']
            elev_loss = seg_data['elev_loss']
            natural_time = natural_results[i]['natural_time']
            
            # Get bounds and cost
            min_mult, max_mult, base_effort_cost = get_terrain_effort_bounds(
                elev_gain, elev_loss, distance_km, climbing_ability, skill_level
            )
            
            # Capacity for adjustment (only slower direction for protect)
            capacity = natural_time * (max_mult - 1.0)
            
            # Total cost (MUST match real allocation - includes cumulative fatigue)
            cumulative_effort_km = sum(
                s['distance'] + (s['elev_gain'] / 100.0) + (s['elev_loss'] / 200.0)
                for s in segments_data[:i]
            )
            
            if fatigue_enabled:
                fitness_fatigue_map = {'untrained': 1.5, 'recreational': 1.3, 'trained': 1.15, 'elite': 1.05}
                fatigue_factor = fitness_fatigue_map.get(fitness_level, 1.3)
                
                # Calculate segment effort
                segment_effort = distance_km + (elev_gain / 100.0) + (elev_loss / 200.0)
                
                # Fatigue multiplier grows with cumulative effort
                fatigue_multiplier = 1.0 + (cumulative_effort_km / 100.0) * (fatigue_factor - 1.0)
                fatigue_multiplier = min(fatigue_multiplier, fatigue_factor)
            else:
                fatigue_multiplier = 1.0
            
            total_cost = base_effort_cost * fatigue_multiplier
            
            adjustments.append({
                'natural_time': natural_time,
                'capacity': capacity,
                'total_cost': total_cost,
                'index': i
            })
            
            if total_cost > 0 and capacity > 0:
                total_weighted_capacity += capacity / total_cost
        
        if total_weighted_capacity == 0:
            return 0.0
        
        # Allocate time based on cost weighting and count segments that hit >= 10%
        segments_at_threshold = 0
        total_segments = len(adjustments)
        
        for adj in adjustments:
            if adj['total_cost'] > 0 and adj['capacity'] > 0:
                weighted_share = (adj['capacity'] / adj['total_cost']) / total_weighted_capacity
                segment_adjustment = min(abs_delta_t * weighted_share, adj['capacity'])
                adjustment_ratio = segment_adjustment / adj['natural_time']
                
                # Only count if going slower AND >=10% adjustment
                if adjustment_ratio >= 0.10:
                    segments_at_threshold += 1
        
        # Return percentage of segments at threshold
        return segments_at_threshold / total_segments if total_segments > 0 else 0.0
    
    # Binary search for push threshold (where >50% of segments hit 10% faster)
    # Search range: 50% to 100% of natural time
    low, high = natural_total_time * 0.5, natural_total_time
    push_threshold = natural_total_time * 0.90  # fallback
    
    for _ in range(20):  # Binary search iterations
        mid = (low + high) / 2.0
        pct_at_threshold = simulate_push_segments(mid)
        
        if abs(pct_at_threshold - 0.50) < 0.05:  # Close enough to 50% of segments
            push_threshold = mid
            break
        elif pct_at_threshold < 0.50:
            high = mid  # Need to go faster (lower target time) to hit more segments
        else:
            low = mid  # Too fast, too many segments affected
    else:
        # Loop completed without break - use midpoint of final range
        push_threshold = (low + high) / 2.0
    
    # Binary search for protect threshold (where >50% of segments hit 10% slower)
    # Search range: 100% to 150% of natural time
    low, high = natural_total_time, natural_total_time * 1.5
    protect_threshold = natural_total_time * 1.10  # fallback
    
    for _ in range(20):  # Binary search iterations
        mid = (low + high) / 2.0
        pct_at_threshold = simulate_protect_segments(mid)
        
        if abs(pct_at_threshold - 0.50) < 0.05:  # Close enough to 50% of segments
            protect_threshold = mid
            break
        elif pct_at_threshold < 0.50:
            low = mid  # Need to go slower (higher target time) to hit more segments
        else:
            high = mid  # Too slow, too many segments affected
    else:
        # Loop completed without break - use midpoint of final range
        protect_threshold = (low + high) / 2.0
    
    # Add checkpoint time to all values so thresholds represent TOTAL race time
    # (Users enter target as total time including stops, so thresholds should too)
    result = {
        'natural_time_minutes': natural_total_time + total_cp_time,
        'push_threshold_minutes': push_threshold + total_cp_time,
        'protect_threshold_minutes': protect_threshold + total_cp_time
    }
    
    # Validate result values to prevent NaN from reaching the UI
    import math
    for key, value in result.items():
        if value is None or (isinstance(value, float) and math.isnan(value)):
            print(f"ERROR: NaN detected in {key}: natural={natural_total_time}, push={push_threshold}, protect={protect_threshold}, cp_time={total_cp_time}")
            return None
    
    print(f"DEBUG threshold result: {result}")
    return result


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
        
        # Target time mode (new feature)
        pacing_mode = data.get('pacing_mode', 'base_pace')  # 'base_pace' or 'target_time'
        target_time_str = data.get('target_time')  # "HH:MM:SS" or None
        
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
            
            # Sanitize filename to prevent path traversal
            from werkzeug.utils import secure_filename
            filename = secure_filename(filename)
            
            # Check if this is a known race or user-uploaded file
            is_known_race = data.get('is_known_race', False)
            
            if is_known_race:
                # Look for file in known races folder
                filepath = os.path.join(app.config['KNOWN_RACES_FOLDER'], filename)
            else:
                # Look for file in upload folder
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            if not os.path.exists(filepath):
                return jsonify({'error': 'GPX file not found'}), 400
            
            # Parse GPX
            trackpoints = parse_gpx_file(filepath)
            total_distance = calculate_total_distance(trackpoints)
            
            # Find checkpoint indices using trackpoints
            checkpoint_indices, distances = find_checkpoint_indices(trackpoints, checkpoint_distances)
        
        # === Prepare segment data for calculations ===
        num_checkpoints = len(checkpoint_distances)
        segment_labels = ["Start"]
        for i in range(num_checkpoints):
            segment_labels.append(f"CP{i + 1}")
        segment_labels.append("Finish")
        
        # Build basic segment info (distance, elevation, terrain)
        segments_basic_data = []
        for i in range(len(checkpoint_indices) - 1):
            start_idx = checkpoint_indices[i]
            end_idx = checkpoint_indices[i + 1]
            
            segment_dist = distances[end_idx] - distances[start_idx]
            elev_gain, elev_loss = calculate_elevation_change(trackpoints, start_idx, end_idx)
            terrain_type = segment_terrain_types[i] if i < len(segment_terrain_types) else 'smooth_trail'
            
            segments_basic_data.append({
                'from': segment_labels[i],
                'to': segment_labels[i + 1],
                'distance': segment_dist,
                'elev_gain': elev_gain,
                'elev_loss': elev_loss,
                'terrain_type': terrain_type
            })
        
        # === Handle Target Time Mode ===
        use_target_time = pacing_mode == 'target_time' and target_time_str
        if use_target_time:
            try:
                # Parse target time (HH:MM:SS)
                time_parts = target_time_str.split(':')
                if len(time_parts) == 3:
                    target_hours = int(time_parts[0])
                    target_minutes = int(time_parts[1])
                    target_seconds = int(time_parts[2])
                    target_total_minutes = target_hours * 60 + target_minutes + target_seconds / 60.0
                    
                    # Subtract CP stop time to get target moving time
                    total_cp_time = avg_cp_time * num_checkpoints
                    target_moving_time = target_total_minutes - total_cp_time
                    
                    if target_moving_time <= 0:
                        return jsonify({'error': f'Target time ({target_time_str}) is too short - checkpoint stops alone require {total_cp_time:.1f} minutes'}), 400
                    
                    log_message(f"\n=== TARGET TIME MODE: Effort Allocation Optimization ===")
                    log_message(f"Target time: {target_time_str} (moving time: {target_moving_time:.2f} min)")
                    
                    # Step 1: Calculate natural pacing (what athlete would do on autopilot)
                    natural_results = calculate_natural_pacing(
                        segments_basic_data, z2_pace, climbing_ability,
                        fatigue_enabled, fitness_level, skill_level
                    )
                    
                    # Step 2: Apply effort allocation optimization
                    reverse_results = allocate_effort_to_target(
                        target_moving_time, segments_basic_data, natural_results,
                        z2_pace, climbing_ability, fatigue_enabled, fitness_level, skill_level
                    )
                else:
                    return jsonify({'error': 'Invalid target time format. Use HH:MM:SS'}), 400
            except Exception as e:
                return jsonify({'error': f'Error parsing target time: {str(e)}'}), 400
        
        # Calculate segments with cumulative effort tracking
        segments = []
        cumulative_time = 0.0
        total_moving_time = 0.0
        cumulative_effort = 0.0  # Track effort in km-effort
        cumulative_distance = 0.0  # Track cumulative distance
        
        for i in range(len(segments_basic_data)):
            seg_basic = segments_basic_data[i]
            segment_dist = seg_basic['distance']
            elev_gain = seg_basic['elev_gain']
            elev_loss = seg_basic['elev_loss']
            terrain_type = seg_basic['terrain_type']
            net_elev_change = elev_gain - elev_loss
            
            # === Calculate segment time and pace ===
            if use_target_time:
                # Target Time Mode: Use effort allocation optimizer
                segment_time = reverse_results[i]['segment_time']
                required_pace = reverse_results[i]['required_pace']
                effort_level = reverse_results[i].get('effort_level', 'steady')
                
                # For display: still calculate what the natural pace would be
                _, elev_adjusted_pace, fatigue_seconds, terrain_factor, _ = adjust_pace_for_elevation(
                    z2_pace, elev_gain, elev_loss, segment_dist, cumulative_effort, climbing_ability,
                    fatigue_enabled, fitness_level, terrain_type, skill_level
                )
                
                # Mark as aggressive if pushing significantly harder than natural
                pace_aggressive = effort_level == 'push'
                adjusted_pace = required_pace
                pace_capped = False
            else:
                # Base Pace Mode: Use forward-calculated pace (prediction)
                adjusted_pace, elev_adjusted_pace, fatigue_seconds, terrain_factor, pace_capped = adjust_pace_for_elevation(
                    z2_pace, elev_gain, elev_loss, segment_dist, cumulative_effort, climbing_ability,
                    fatigue_enabled, fitness_level, terrain_type, skill_level
                )
                segment_time = segment_dist * adjusted_pace
                pace_aggressive = False
                effort_level = 'steady'
                
                # Log when pace is capped
                if pace_capped:
                    segment_label = f"{seg_basic['from']} → {seg_basic['to']}"
                    print(f"⚠️  PACE CAPPED: {segment_label} - Pace limited to {adjusted_pace:.2f} min/km (2.5× base pace)")
            
            # Update cumulative effort: effort_km = distance_km + ascent_m/100 + descent_m/200
            segment_effort = segment_dist + (elev_gain / 100.0) + (elev_loss / 200.0)
            cumulative_effort += segment_effort
            cumulative_distance += segment_dist
            
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
                'from': seg_basic['from'],
                'to': seg_basic['to'],
                'distance': round(segment_dist, 2),
                'cumulative_distance': round(cumulative_distance, 2),
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
                'pace_aggressive': pace_aggressive if use_target_time else False,
                'effort_level': effort_level if use_target_time else 'steady',  # New: effort allocation
                # Note: In target time mode, fatigue is incorporated into natural pacing, not displayed separately
                'fatigue_seconds': round(fatigue_seconds, 1) if not use_target_time else 0.0,
                'fatigue_str': f"+{int(fatigue_seconds // 60)}:{int(fatigue_seconds % 60):02d}" if not use_target_time else "+0:00",
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
        
        # Calculate effort thresholds for target time mode
        effort_thresholds = None
        if use_target_time and natural_results:
            num_checkpoints = len(checkpoint_distances)  # Includes finish but not start
            effort_thresholds = calculate_effort_thresholds(
                natural_results, segments_basic_data, z2_pace,
                climbing_ability, fatigue_enabled, fitness_level, skill_level,
                num_checkpoints, avg_cp_time
            )
        
        response_data = {
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
        }
        
        # Add effort thresholds if in target time mode
        if effort_thresholds:
            response_data['effort_thresholds'] = effort_thresholds
        
        return jsonify(response_data)
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
        
        log_message(f"🚀 SAVE PLAN REQUEST START - Plan name: '{plan_name}'")
        log_message(f"   Supabase enabled: {is_supabase_enabled()}")
        
        # Try Supabase first if enabled
        if is_supabase_enabled():
            user_info = get_user_id_from_request()
            log_message(f"   User info from request: {user_info}")
            
            if user_info:
                log_message(f"📝 Save plan request - User type: {user_info.get('type')}, ID: {user_info.get('id')}")
                try:
                    # Determine owner_id or anonymous_id
                    owner_id = user_info['id'] if user_info['type'] == 'authenticated' else None
                    anonymous_id = user_info['id'] if user_info['type'] == 'anonymous' else None
                    
                    log_message(f"  Plan name: '{plan_name}'")
                    log_message(f"  Owner ID: {owner_id}")
                    log_message(f"  Anonymous ID: {anonymous_id}")
                    
                    # Use admin client for authenticated users (bypasses RLS since we've already validated)
                    # Use regular client for anonymous users (RLS allows anonymous_id based access)
                    client = get_supabase_admin_client() if owner_id else get_supabase_client()
                    if not client:
                        # For authenticated users, this is a configuration error - don't fall back
                        if owner_id:
                            error_msg = "Supabase admin client not available. SUPABASE_SERVICE_KEY may not be set."
                            log_message(f"ERROR: {error_msg}")
                            return jsonify({'error': error_msg}), 500
                        # For anonymous users, fall through to file-based storage
                        raise Exception("Supabase client not available for anonymous user")
                    
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
                        
                        # Verify the update succeeded
                        if hasattr(result, 'error') and result.error:
                            error_msg = f"Failed to update plan: {result.error}"
                            log_message(f"❌ {error_msg}")
                            return jsonify({'error': error_msg}), 500
                        
                        if not result.data:
                            error_msg = f"Update returned no data - operation may have failed"
                            log_message(f"❌ {error_msg}")
                            return jsonify({'error': error_msg}), 500
                            
                        log_message(f"✓ Updated plan '{plan_name}' for user {owner_id or anonymous_id}")
                        log_message(f"  Result data: {result.data}")
                    else:
                        # Insert new plan
                        result = client.table('user_plans').insert(plan_record).execute()
                        
                        # Verify the insert succeeded
                        if hasattr(result, 'error') and result.error:
                            error_msg = f"Failed to insert plan: {result.error}"
                            log_message(f"❌ {error_msg}")
                            return jsonify({'error': error_msg}), 500
                        
                        if not result.data:
                            error_msg = f"Insert returned no data - operation may have failed. Check RLS policies."
                            log_message(f"❌ {error_msg}")
                            log_message(f"  Attempted insert with owner_id={owner_id}, anonymous_id={anonymous_id}")
                            return jsonify({'error': error_msg}), 500
                            
                        log_message(f"✓ Inserted new plan '{plan_name}' for user {owner_id or anonymous_id}")
                        log_message(f"  Result data: {result.data}")
                    
                    return jsonify({'message': 'Plan saved successfully', 'filename': f"{plan_name}.json"})
                except Exception as e:
                    log_message(f"Supabase save error: {e}")
                    import traceback
                    traceback.print_exc()
                    sys.stdout.flush()
                    # For authenticated users, return error instead of falling back
                    if user_info.get('type') == 'authenticated':
                        return jsonify({'error': f'Failed to save plan to database: {str(e)}'}), 500
                    # Fall through to file-based storage for anonymous users
            else:
                log_message(f"⚠️  No user_info - falling back to file-based storage")
        else:
            log_message(f"⚠️  Supabase not enabled - falling back to file-based storage")
        
        # Fall back to file-based storage
        log_message(f"💾 Using file-based storage for plan: '{plan_name}'")
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
    """List all saved race plans - always includes local plans + Supabase plans if authenticated."""
    try:
        plans = []
        
        # Always load local file-based plans first
        if os.path.exists(app.config['SAVED_PLANS_FOLDER']):
            for filename in os.listdir(app.config['SAVED_PLANS_FOLDER']):
                if filename.endswith('.json'):
                    filepath = os.path.join(app.config['SAVED_PLANS_FOLDER'], filename)
                    modified_time = os.path.getmtime(filepath)
                    plans.append({
                        'filename': filename,
                        'name': filename.replace('.json', ''),
                        'modified': datetime.fromtimestamp(modified_time).strftime('%Y-%m-%d %H:%M:%S'),
                        'source': 'local'  # Mark as local plan
                    })
        
        # Additionally load Supabase plans if enabled and user is identified (authenticated or anonymous)
        if is_supabase_enabled():
            user_info = get_user_id_from_request()
            
            # Load cloud plans for both authenticated and anonymous users
            if user_info:
                try:
                    # Use admin client for authenticated users, regular client for anonymous
                    client = get_supabase_admin_client() if user_info['type'] == 'authenticated' else get_supabase_client()
                    if client:
                        # Query plans based on user type
                        query = client.table('user_plans').select('id, plan_name, created_at, updated_at')
                        
                        if user_info['type'] == 'authenticated':
                            query = query.eq('owner_id', user_info['id'])
                        else:  # anonymous
                            query = query.eq('anonymous_id', user_info['id'])
                        
                        result = query.order('updated_at', desc=True).execute()
                        
                        for plan in result.data:
                            plans.append({
                                'filename': f"{plan['plan_name']}.json",
                                'name': plan['plan_name'],
                                'modified': plan['updated_at'][:19].replace('T', ' '),
                                'source': 'cloud'  # Mark as cloud plan
                            })
                except Exception as e:
                    print(f"Supabase list error: {e}")
                    # Continue with local plans only
        
        # Sort all plans by modified date
        plans.sort(key=lambda x: x['modified'], reverse=True)
        return jsonify({'plans': plans})
    except Exception as e:
        print(f"List plans error: {e}")
        return jsonify({'error': str(e)}), 400

@app.route('/api/load-plan/<filename>', methods=['GET'])
def load_plan(filename):
    """Load a saved race plan - supports both local and cloud storage."""
    try:
        # Get source parameter from query string (local or cloud)
        source = request.args.get('source', 'local')
        plan_name = filename.replace('.json', '')
        
        # If source is explicitly 'local', load from disk
        if source == 'local':
            filepath = os.path.join(app.config['SAVED_PLANS_FOLDER'], secure_filename(filename))
            
            if not os.path.exists(filepath):
                return jsonify({'error': 'Plan not found'}), 404
            
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            return jsonify(data)
        
        # If source is 'cloud', try Supabase
        elif source == 'cloud':
            if not is_supabase_enabled():
                return jsonify({'error': 'Cloud storage not available'}), 400
            
            user_info = get_user_id_from_request()
            
            if not user_info:
                return jsonify({'error': 'User identification required for cloud plans'}), 401
            
            try:
                # Use admin client for authenticated users, regular client for anonymous
                client = get_supabase_admin_client() if user_info['type'] == 'authenticated' else get_supabase_client()
                if not client:
                    return jsonify({'error': 'Cloud storage not available'}), 500
                
                query = client.table('user_plans').select('plan_data')
                
                if user_info['type'] == 'authenticated':
                    query = query.eq('owner_id', user_info['id'])
                else:  # anonymous
                    query = query.eq('anonymous_id', user_info['id'])
                
                query = query.eq('plan_name', plan_name)
                result = query.execute()
                
                if result.data:
                    return jsonify(result.data[0]['plan_data'])
                else:
                    return jsonify({'error': 'Plan not found'}), 404
            except Exception as e:
                print(f"Supabase load error: {e}")
                return jsonify({'error': 'Failed to load plan from cloud'}), 500
        
        # If source is 'unowned', load anonymous/unowned Supabase plan (requires admin access)
        elif source == 'unowned':
            if not is_supabase_enabled():
                return jsonify({'error': 'Cloud storage not available'}), 400
            
            try:
                admin_client = get_supabase_admin_client()
                if not admin_client:
                    return jsonify({'error': 'Cloud storage not available'}), 500
                
                # Load unowned plan by name (plan with anonymous_id but no owner_id)
                result = admin_client.table('user_plans').select('plan_data').eq('plan_name', plan_name).is_('owner_id', 'null').not_.is_('anonymous_id', 'null').execute()
                
                if result.data:
                    return jsonify(result.data[0]['plan_data'])
                else:
                    return jsonify({'error': 'Plan not found'}), 404
            except Exception as e:
                print(f"Supabase load unowned plan error: {e}")
                return jsonify({'error': 'Failed to load plan from cloud'}), 500
        
        else:
            return jsonify({'error': 'Invalid source parameter'}), 400
            
    except Exception as e:
        print(f"Load plan error: {e}")
        return jsonify({'error': str(e)}), 400

@app.route('/api/delete-plan/<filename>', methods=['DELETE'])
def delete_plan(filename):
    """Delete a saved race plan - supports both local and cloud storage."""
    try:
        # Get source parameter from query string (local or cloud)
        source = request.args.get('source', 'local')
        plan_name = filename.replace('.json', '')
        
        # If source is explicitly 'local', delete from disk
        if source == 'local':
            filepath = os.path.join(app.config['SAVED_PLANS_FOLDER'], secure_filename(filename))
            
            if not os.path.exists(filepath):
                return jsonify({'error': 'Plan not found'}), 404
            
            os.remove(filepath)
            return jsonify({'message': 'Plan deleted successfully'})
        
        # If source is 'cloud', delete from Supabase
        elif source == 'cloud':
            if not is_supabase_enabled():
                return jsonify({'error': 'Cloud storage not available'}), 400
            
            user_info = get_user_id_from_request()
            
            if not user_info:
                return jsonify({'error': 'User identification required for cloud plans'}), 401
            
            try:
                # Use admin client for authenticated users, regular client for anonymous
                client = get_supabase_admin_client() if user_info['type'] == 'authenticated' else get_supabase_client()
                if not client:
                    return jsonify({'error': 'Cloud storage not available'}), 500
                
                query = client.table('user_plans').delete()
                
                if user_info['type'] == 'authenticated':
                    query = query.eq('owner_id', user_info['id'])
                else:  # anonymous
                    query = query.eq('anonymous_id', user_info['id'])
                
                query = query.eq('plan_name', plan_name)
                result = query.execute()
                
                if result.data:
                    return jsonify({'message': 'Plan deleted successfully'})
                else:
                    return jsonify({'error': 'Plan not found'}), 404
            except Exception as e:
                print(f"Supabase delete error: {e}")
                return jsonify({'error': 'Failed to delete plan from cloud'}), 500
        
        else:
            return jsonify({'error': 'Invalid source parameter'}), 400
            
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
        header = ['Segment', 'Cumulative Distance (km)', 'Elev Gain (m)', 'Elev Loss (m)', 'Net Elev (m)', 
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
                seg['cumulative_distance'],
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


@app.route('/api/auth/diagnose', methods=['GET'])
def diagnose_supabase():
    """Diagnostic endpoint to check Supabase configuration."""
    diagnostics = {
        'supabase_enabled': is_supabase_enabled(),
        'supabase_url_set': SUPABASE_URL is not None,
        'supabase_anon_key_set': SUPABASE_ANON_KEY is not None,
        'supabase_service_key_set': SUPABASE_SERVICE_KEY is not None,
        'supabase_import_available': supabase_import_available,
        'anon_client_initialized': supabase_client is not None,
        'admin_client_initialized': supabase_admin_client is not None,
    }
    
    # Try to initialize clients if not already done
    if is_supabase_enabled():
        # Try anon client with error capture
        anon_client = None
        anon_error = None
        try:
            if supabase_client is None and supabase_import_available:
                from supabase import create_client
                anon_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        except Exception as e:
            anon_error = str(e)
            import traceback
            anon_error_detail = traceback.format_exc()
            print(f"Anon client initialization error: {anon_error_detail}")
        
        if anon_client is None:
            anon_client = supabase_client
        
        diagnostics['anon_client_available'] = anon_client is not None
        if anon_error:
            diagnostics['anon_client_error'] = anon_error
        
        # Try admin client with error capture
        admin_client = None
        admin_error = None
        try:
            if supabase_admin_client is None and supabase_import_available and SUPABASE_SERVICE_KEY:
                from supabase import create_client
                admin_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        except Exception as e:
            admin_error = str(e)
            import traceback
            admin_error_detail = traceback.format_exc()
            print(f"Admin client initialization error: {admin_error_detail}")
        
        if admin_client is None:
            admin_client = supabase_admin_client
            
        diagnostics['admin_client_available'] = admin_client is not None
        if admin_error:
            diagnostics['admin_client_error'] = admin_error
        
        # Test admin client connection
        if admin_client:
            try:
                # Try a simple query to verify connection
                result = admin_client.table('user_plans').select('id').limit(1).execute()
                diagnostics['admin_client_connection'] = 'success'
                diagnostics['user_plans_table_accessible'] = True
            except Exception as e:
                diagnostics['admin_client_connection'] = f'failed: {str(e)}'
                diagnostics['user_plans_table_accessible'] = False
    
    return jsonify(diagnostics)


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


@app.route('/api/auth/list-local-plans', methods=['GET'])
def list_local_plans():
    """List all plans saved locally on disk."""
    try:
        plans = []
        if os.path.exists(app.config['SAVED_PLANS_FOLDER']):
            for filename in os.listdir(app.config['SAVED_PLANS_FOLDER']):
                if filename.endswith('.json'):
                    filepath = os.path.join(app.config['SAVED_PLANS_FOLDER'], filename)
                    modified_time = os.path.getmtime(filepath)
                    plans.append({
                        'id': filename,  # Use filename as ID for local plans
                        'name': filename.replace('.json', ''),
                        'created_at': datetime.fromtimestamp(modified_time).strftime('%Y-%m-%d %H:%M:%S'),
                        'updated_at': datetime.fromtimestamp(modified_time).strftime('%Y-%m-%d %H:%M:%S')
                    })
        
        # Sort by modification time
        plans.sort(key=lambda x: x['updated_at'], reverse=True)
        return jsonify({'plans': plans})
    except Exception as e:
        print(f"List local plans error: {e}")
        return jsonify({'error': str(e)}), 400


@app.route('/api/list-unowned-plans', methods=['GET'])
def list_unowned_plans():
    """List all local plans and anonymous Supabase plans (unowned plans)."""
    try:
        plans = []
        
        # Get local disk plans
        if os.path.exists(app.config['SAVED_PLANS_FOLDER']):
            for filename in os.listdir(app.config['SAVED_PLANS_FOLDER']):
                if filename.endswith('.json'):
                    filepath = os.path.join(app.config['SAVED_PLANS_FOLDER'], filename)
                    modified_time = os.path.getmtime(filepath)
                    plans.append({
                        'filename': filename,
                        'name': filename.replace('.json', ''),
                        'modified': datetime.fromtimestamp(modified_time).strftime('%Y-%m-%d %H:%M:%S'),
                        'source': 'local'  # Mark as local plan
                    })
        
        # Get anonymous Supabase plans (plans with anonymous_id but no owner_id)
        if is_supabase_enabled():
            try:
                admin_client = get_supabase_admin_client()
                if admin_client:
                    # Query plans that have anonymous_id but no owner_id (unowned plans)
                    result = admin_client.table('user_plans').select('id, plan_name, created_at, updated_at, anonymous_id').is_('owner_id', 'null').not_.is_('anonymous_id', 'null').order('updated_at', desc=True).execute()
                    
                    for plan in result.data:
                        plans.append({
                            'filename': f"{plan['plan_name']}.json",
                            'name': plan['plan_name'],
                            'modified': plan['updated_at'][:19].replace('T', ' '),
                            'source': 'unowned',  # Mark as unowned Supabase plan
                            'anonymous_id': plan['anonymous_id'],  # Include for claiming
                            'plan_id': plan['id']  # Include plan ID for claiming
                        })
            except Exception as e:
                print(f"Error fetching unowned Supabase plans: {e}")
                # Continue with local plans only
        
        # Sort all plans by modified date
        plans.sort(key=lambda x: x['modified'], reverse=True)
        return jsonify({'plans': plans})
    except Exception as e:
        print(f"List unowned plans error: {e}")
        return jsonify({'error': str(e)}), 400


@app.route('/api/auth/migrate-local-plan', methods=['POST'])
def migrate_local_plan():
    """Migrate a single local plan to authenticated user's Supabase account."""
    if not is_supabase_enabled():
        return jsonify({'error': 'Supabase is not configured'}), 400
    
    try:
        data = request.json
        auth_header = request.headers.get('Authorization')
        filename = data.get('filename')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authorization header required'}), 401
        
        if not filename:
            return jsonify({'error': 'Filename required'}), 400
        
        # Get authenticated user
        token = auth_header.replace('Bearer ', '')
        user = get_supabase_client().auth.get_user(token)
        
        if not user or not hasattr(user, 'user') or not user.user:
            return jsonify({'error': 'Invalid authentication token'}), 401
        
        user_id = user.user.id
        
        # Read the local plan file
        filepath = os.path.join(app.config['SAVED_PLANS_FOLDER'], secure_filename(filename))
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'Plan not found'}), 404
        
        with open(filepath, 'r') as f:
            plan_data = json.load(f)
        
        plan_name = filename.replace('.json', '')
        
        # Save to Supabase
        admin_client = get_supabase_admin_client()
        if not admin_client:
            return jsonify({'error': 'Migration service not available'}), 500
        
        # Check if plan already exists
        existing = admin_client.table('user_plans').select('id').eq('owner_id', user_id).eq('plan_name', plan_name).execute()
        
        if existing.data:
            # Update existing plan
            result = admin_client.table('user_plans').update({
                'plan_data': plan_data,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }).eq('owner_id', user_id).eq('plan_name', plan_name).execute()
        else:
            # Insert new plan
            result = admin_client.table('user_plans').insert({
                'owner_id': user_id,
                'plan_name': plan_name,
                'plan_data': plan_data,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }).execute()
        
        # Delete the local file after successful migration
        if result.data:
            os.remove(filepath)
            return jsonify({
                'message': 'Plan migrated successfully',
                'plan_name': plan_name
            })
        else:
            return jsonify({'error': 'Failed to migrate plan'}), 500
            
    except Exception as e:
        print(f"Migration error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Migration failed: {str(e)}'}), 500


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


@app.route('/api/auth/claim-unowned-plan', methods=['POST'])
def claim_unowned_plan():
    """Claim an unowned/anonymous plan by updating owner_id for authenticated user."""
    if not is_supabase_enabled():
        return jsonify({'error': 'Supabase is not configured'}), 400
    
    try:
        data = request.json
        auth_header = request.headers.get('Authorization')
        plan_id = data.get('plan_id')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authorization header required'}), 401
        
        if not plan_id:
            return jsonify({'error': 'Plan ID required'}), 400
        
        # Get authenticated user
        token = auth_header.replace('Bearer ', '')
        user = get_supabase_client().auth.get_user(token)
        
        if not user or not hasattr(user, 'user') or not user.user:
            return jsonify({'error': 'Invalid authentication token'}), 401
        
        user_id = user.user.id
        
        # Update the plan to set owner_id
        admin_client = get_supabase_admin_client()
        if not admin_client:
            return jsonify({'error': 'Service not available'}), 500
        
        # First verify the plan exists and is unowned
        check_result = admin_client.table('user_plans').select('id, plan_name').eq('id', plan_id).is_('owner_id', 'null').not_.is_('anonymous_id', 'null').execute()
        
        if not check_result.data:
            return jsonify({'error': 'Plan not found or already owned'}), 404
        
        plan_name = check_result.data[0]['plan_name']
        
        # Check if user already has a plan with the same name
        existing = admin_client.table('user_plans').select('id').eq('owner_id', user_id).eq('plan_name', plan_name).execute()
        
        if existing.data:
            return jsonify({'error': f'You already have a plan named "{plan_name}". Please rename or delete it first.'}), 409
        
        # Update the plan to claim ownership
        result = admin_client.table('user_plans').update({
            'owner_id': user_id,
            'updated_at': datetime.now(timezone.utc).isoformat()
        }).eq('id', plan_id).execute()
        
        if result.data:
            return jsonify({
                'message': 'Plan claimed successfully',
                'plan_name': plan_name
            })
        else:
            return jsonify({'error': 'Failed to claim plan'}), 500
            
    except Exception as e:
        print(f"Claim plan error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to claim plan: {str(e)}'}), 500


if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', '0').lower() in ('1', 'true')
    app.run(host='0.0.0.0', port=5001, debug=debug_mode)
