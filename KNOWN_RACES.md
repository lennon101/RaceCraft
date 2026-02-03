# Known Races Feature

## Overview

The "Load Known Race" feature allows users to quickly load predefined race routes from a curated library of GPX files. This eliminates the need to manually upload GPX files for popular or commonly-used races.

## Directory Structure

Known race GPX files are stored in:
- **Docker/Production**: `/app/static_data/known_races/` (read-only, bundled in the image)
- **Local Development**: `data/known_races/` (primary) or `FuelPlanData/known_races/` (fallback)

**Note**: In Docker deployments, known races are stored outside the `/app/data` directory to ensure they remain accessible even when users mount volumes for persistent data storage.

## GPX File Naming Convention

GPX files must follow this specific naming format:

```
Organiser-race_name-year.gpx
```

### Examples

- `UTMB-Mont_Blanc_100-2024.gpx`
- `Ironman-Taupo-2023.gpx`
- `Salomon-Kosci_Miler-2022.gpx`

### Naming Rules

1. **Organiser**: Text before the first `-` (e.g., `UTMB`, `Ironman`, `Salomon`)
2. **Race Name**: Text between first `-` and last `-` (e.g., `Mont_Blanc_100`, `Taupo`)
   - Use underscores `_` instead of spaces in race names
   - Underscores are automatically converted to spaces in the UI
3. **Year**: 4-digit year as the last component (e.g., `2024`, `2023`)

## Using the Feature

### Loading a Known Race

1. Click the **"Load Known Race"** button in the GPX Upload section
2. Browse races grouped by organiser
3. Use the search box to filter by:
   - Race name
   - Race organiser
   - Year
4. Click "Load" on the desired race

### Search Functionality

The search supports partial matching:
- Search "2024" to find all 2024 races
- Search "UTMB" to find all UTMB races
- Search "Mont Blanc" to find races with "Mont Blanc" in the name

## Adding New Known Races

### For Bundled Races (Docker)

1. Add GPX file to `data/known_races/` directory following the naming convention
2. Rebuild the Docker image
3. The race will be available in all deployments

### For Local Development

1. Add GPX file to `data/known_races/` directory (or `FuelPlanData/known_races/` for legacy setups)
2. Follow the naming convention: `Organiser-race_name-year.gpx`
3. Restart the Flask application
3. The race will appear in the known races modal

## API Endpoints

### List Known Races

```
GET /api/list-known-races
```

Returns:
```json
{
  "races": [...],
  "grouped": {
    "UTMB": [
      {
        "filename": "UTMB-Mont_Blanc_100-2024.gpx",
        "organiser": "UTMB",
        "race_name": "Mont Blanc 100",
        "year": 2024
      }
    ]
  }
}
```

### Load Known Race

```
GET /api/load-known-race/<filename>
```

Returns the same format as `/api/upload-gpx` plus metadata:
```json
{
  "filename": "UTMB-Mont_Blanc_100-2024.gpx",
  "total_distance": 171.0,
  "total_distance_miles": 106.25,
  "total_elev_gain": 9978.0,
  "total_elev_loss": 9978.0,
  "num_trackpoints": 3500,
  "metadata": {
    "organiser": "UTMB",
    "race_name": "Mont Blanc 100",
    "year": 2024
  },
  "is_known_race": true
}
```

## Benefits

- **Faster onboarding**: New users can try the app immediately with example races
- **Reduced friction**: No need to find and download GPX files for popular races
- **Consistency**: Validated, high-quality GPX data
- **Reference planning**: Compare different race options quickly

## Implementation Details

- Known races are **read-only** - they cannot be modified through the UI
- Files are served directly from the filesystem
- Filename parsing is done server-side for security
- Search filtering is performed client-side for responsiveness
- Known races integrate seamlessly with the existing GPX upload pipeline

## Future Enhancements

Potential improvements for future versions:

- Display race statistics (distance, elevation) in the selection list
- Support multiple race distances for the same event and year
- Allow race organisers to submit official GPX updates
- Add race categories/tags (trail, road, ultra, etc.)
- Include race descriptions and metadata (cutoff times, aid stations)
