# Race Fuel & Pacing Planner

A Python tool for ultra-running race planning that calculates personalized pacing, fuel requirements, and hydration needs based on your GPX route file and individual performance characteristics.

## Features

- **GPX Route Analysis**: Automatically parses GPX files (supports both track and route formats) to extract distance and elevation data
- **Personalized Pace Calculations**: Adjusts pace based on elevation changes, accumulated fatigue, and terrain
- **Fuel & Hydration Planning**: Calculates carbohydrate and water intake targets for each segment
- **Checkpoint Management**: Plan your race with custom checkpoint distances and stop times
- **Previous Race Calibration**: Option to calculate personalized elevation gain factors from past race results

## Requirements

- Python 3.x
- No external dependencies (uses only standard library)

## Setup

1. Place your GPX file(s) in the same directory as `Fuel-Plan.py`
2. Run the script: `python Fuel-Plan.py`
3. Select which GPX file to use from the list presented

## Configuration Constants

### GPX_FILENAME
- **Default**: `"route.gpx"`
- **Description**: Name of the GPX file containing your race route

### ELEVATION_GAIN_FACTOR
- **Default**: `6.0` seconds per meter
- **Description**: Time penalty added per meter of elevation gain. Based on Naismith's rule (~10 seconds/meter for hiking). Lower values for stronger climbers, higher values for those who struggle with elevation.
- **Can be calculated**: The tool can calculate this from a previous race performance

### FATIGUE_MULTIPLIER
- **Default**: `2.0` percent per hour
- **Description**: Percentage pace slowdown per hour of running. Represents cumulative fatigue effect.
  - `0.5` = Very fit, maintains pace well (0.5% slower per hour)
  - `2.0` = Moderate fatigue accumulation (2% slower per hour)
  - `5.0` = Significant fatigue issues (5% slower per hour)
- **Example**: With `2.0`, after 10 hours you'll be ~20% slower than fresh pace

### MAX_DOWNHILL_SPEED_INCREASE
- **Default**: `20.0` percent
- **Description**: Maximum percentage your pace can increase on downhills. Prevents unrealistic fast paces.
- **Example**: If Z2 pace is 6:00 min/km, fastest allowed pace is 4:48 min/km (20% faster)

### DEFAULT_CARBS_PER_HOUR
- **Default**: `60.0` grams
- **Description**: Target carbohydrate intake per hour
- **Typical ranges**:
  - 30-60g/hr: Lower intensity or smaller athletes
  - 60-90g/hr: Standard ultra running recommendation
  - 90-120g/hr: High-intensity or trained gut tolerance

### DEFAULT_WATER_PER_HOUR
- **Default**: `500.0` mL
- **Description**: Target water intake per hour
- **Typical ranges**:
  - 400-500 mL/hr: Cool conditions, lower intensity
  - 500-750 mL/hr: Moderate conditions
  - 750-1000+ mL/hr: Hot conditions, high sweat rate

## How It Works

### Pace Calculation

The tool calculates adjusted pace for each segment through multiple steps:

1. **Base Pace**: Your Zone 2 pace on flat ground (comfortable aerobic pace)

2. **Elevation Adjustment**:
   ```
   Elevation Time = (gain × factor) - (loss × factor × 0.3)
   Elevation-Adjusted Pace = (distance × base_pace + elevation_time) / distance
   ```
   - Gains add time (full factor)
   - Losses subtract time (30% of factor, as downhills aren't as beneficial)

3. **Downhill Speed Limit**:
   ```
   Minimum Pace = Base Pace × (1 - MAX_DOWNHILL_SPEED_INCREASE/100)
   ```
   - Applied to elevation-adjusted pace to prevent unrealistic fast speeds

4. **Fatigue Adjustment**: 
   ```
   Fatigue Factor = 1 + (cumulative_hours × FATIGUE_MULTIPLIER / 100)
   Final Pace = Limited Elevation Pace × Fatigue Factor
   ```
   - Applied last to show accumulating tiredness over the race

5. **Maximum Slowness Limit**:
   - Slowest pace: Base × 2.0

### Fuel & Hydration Calculation

For each segment:
```
Target Carbs = (segment_hours × carbs_per_hour) rounded to nearest 10g
Target Water = (segment_hours × water_per_hour) rounded to nearest 50mL
```

## Usage

### Basic Workflow

1. **Start the tool**: `python Fuel-Plan.py`

2. **Select GPX file**:
   - Tool displays all `.gpx` files in the directory
   - Enter the number corresponding to your route

3. **Calculate elevation factor** (optional):
   - Answer 'y' to use previous race data
   - Enter race distance, elevation gain, moving time, and estimated flat pace
   - Tool calculates personalized elevation factor

4. **Enter race details**:
   - Number of checkpoints
   - Expected time at each checkpoint (aid station stops)
   - Distance to each checkpoint (must be in order, cannot exceed total distance)

5. **Enter your pacing**:
   - Zone 2 pace on flat ground (format: MM:SS, e.g., `6:30` for 6:30 min/km)
   - Input validation ensures proper format and valid values

6. **Enter race start time** (optional):
   - Format: HH:MM (e.g., `06:00` for 6:00 AM)
   - Press Enter to skip if you don't want time-of-day calculations

7. **Set nutrition targets**:
   - Carbs per hour (press Enter for default 60g)
   - Water per hour (press Enter for default 500mL)

### Output

The tool displays a detailed table showing for each segment:
- **Segment**: From/to checkpoint labels
- **Dist(km)**: Segment distance
- **Elev+/-**: Elevation gain/loss in meters
- **Net(m)**: Net elevation change (gain - loss)
- **Elev Pace**: Pace adjusted for elevation only (min/km)
- **Fatigue**: Time added per km due to accumulated fatigue (mm:ss)
- **Final Pace**: Final pace including all adjustments (min/km)
- **Time**: Time to complete segment
- **Carbs(g)**: Target carbohydrate intake
- **Water(L)**: Target water intake in liters
- **Cumul Time**: Cumulative race time including checkpoint stops
- **Time of Day**: Clock time at checkpoint (only if race start time provided)

Summary totals include:
- Total moving time (running only)
- Total checkpoint time
- Total race time (moving + checkpoints)
- Total distance
- Total elevation gain
- Total carbs needed
- Total water needed

## Example

```
Available GPX files:
  1. route.gpx
  2. backup-route.gpx

Select a GPX file (1-2): 1

Using GPX file: route.gpx
Total route distance: 100.00 km (62.14 miles)

Do you want to calculate elevation gain factor from a previous race? (y/n): n
Using default elevation gain factor: 6.00 seconds per meter

Number of checkpoints (not including start/finish): 3
Average expected time at each checkpoint (minutes): 5

Enter the distance marker for each checkpoint:
  Checkpoint 1 distance (km): 25
  Checkpoint 2 distance (km): 50
  Checkpoint 3 distance (km): 75

Enter your Zone 2 pace on flat ground:
  (format: MM:SS per km, e.g., 6:30): 6:30

Enter race start time (optional, press Enter to skip):
  (format: HH:MM, e.g., 06:00): 06:00

Target carbs per hour in grams (default: 60g, press Enter to use default): 
Target water per hour in mL (default: 500mL, press Enter to use default): 

CALCULATING RACE PLAN...
...
```

## Tips for Best Results

1. **Accurate Z2 Pace**: Use a pace you can maintain comfortably for hours on flat ground
2. **GPX Quality**: Higher resolution GPX files (more points) provide better accuracy
3. **Previous Race Calibration**: If available, use a similar race type (trail vs road) for elevation factor calculation
4. **Adjust Constants**: Tune FATIGUE_MULTIPLIER based on your experience in ultra distances
5. **Checkpoint Stops**: Include realistic stop times - underestimating here throws off later segments

## GPX File Format

The tool supports:
- **Track points** (`<trkpt>` in `<trk>` elements)
- **Route points** (`<rtept>` in `<rte>` elements)
- With or without XML namespaces
- Exported from most GPS devices and route planning apps (Garmin, Strava, Footpath, etc.)

## Limitations

- Assumes relatively consistent pace between track points
- Does not account for technical terrain difficulty (beyond elevation)
- Weather conditions not factored into calculations
- Individual variability in nutrition/hydration needs

## Customization

All constants can be adjusted at the top of `Fuel-Plan.py`:

```python
GPX_FILENAME = "your-route.gpx"
ELEVATION_GAIN_FACTOR = 6.0
FATIGUE_MULTIPLIER = 2.0
MAX_DOWNHILL_SPEED_INCREASE = 20.0
DEFAULT_CARBS_PER_HOUR = 60.0
DEFAULT_WATER_PER_HOUR = 500.0
```

## License

Free to use and modify for personal use.
