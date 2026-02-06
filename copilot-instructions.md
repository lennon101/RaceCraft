# Copilot Instructions for RaceCraft

## Overview

RaceCraft is a web-based race planner for endurance athletes that estimates pacing, checkpoint timings, fuel requirements, and hydration needs. The application is built with:

- **Backend**: Python 3 with Flask 3.0.0
- **Frontend**: Vanilla JavaScript (no frameworks), HTML5, CSS3
- **Deployment**: Docker containerization with Docker Hub publishing
- **Storage**: JSON files for saved plans, file system for GPX uploads

### Key Features
- GPX route upload and parsing
- Advanced fatigue model with fitness-dependent calculations
- Terrain difficulty system with skill adjustment
- Climbing model using vertical speed (600-1500 m/h)
- Real-time pacing calculations
- Save/load race plans
- CSV export functionality

## Project Structure

```
RaceCraft/
├── app.py                      # Flask backend API (main application)
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker container configuration
├── docker-compose.yml          # Docker Compose setup
├── test_climbing_model.py      # Test script for climbing model
├── templates/
│   └── index.html              # Main HTML page
├── static/
│   ├── css/                    # Stylesheets
│   ├── js/                     # Frontend JavaScript
│   └── uploads/                # GPX file storage (runtime)
├── saved_plans/                # Saved race plans in JSON format (runtime)
├── .github/
│   └── workflows/
│       └── docker-publish.yml  # Docker Hub publishing workflow
├── FATIGUE_MODEL.md            # Fatigue model documentation
├── CLIMBING_MODEL.md           # Climbing model documentation
└── TERRAIN_DIFFICULTY.md       # Terrain difficulty documentation
```

## Setup & Build

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py

# Run tests (for climbing model)
python test_climbing_model.py
```

### Docker Development
```bash
# Build image
docker build -t racecraft .

# Run with Docker Compose
docker compose up -d

# View logs
docker logs racecraft
```

### Testing
- Run climbing model tests: `python test_climbing_model.py`
- Manual testing: Start the app and test GPX upload, calculations, save/load, and CSV export at `http://localhost:5000`

## Code Style & Conventions

### Python (Backend)
- Follow PEP 8 style guidelines
- Use descriptive variable names (e.g., `fitness_level`, `climbing_ability`, `terrain_type`)
- Document complex calculations with inline comments
- Use type hints where it improves clarity
- Prefer explicit over implicit
- Keep functions focused and single-purpose

### JavaScript (Frontend)
- Use vanilla JavaScript (no frameworks like React/Vue)
- Use modern ES6+ syntax (const/let, arrow functions, async/await)
- Use descriptive function and variable names
- Add comments for complex UI logic
- Handle errors gracefully with user-friendly messages

### HTML/CSS
- Use semantic HTML5 elements
- Keep styles modular and organized
- Use CSS Grid and Flexbox for layouts
- Maintain responsive design for mobile compatibility

### API Conventions
- RESTful endpoints with clear naming (e.g., `/api/upload-gpx`, `/api/calculate`)
- Return JSON responses with consistent structure
- Include appropriate HTTP status codes
- Handle errors gracefully with descriptive messages

## Important Constants & Models

### Climbing Model (v1.0.0+)
- **BREAKING CHANGE**: `climbing_ability` replaces `elev_gain_factor` in API
- Vertical speed climbing model: 600-1500 m/h based on ability (conservative: 600, moderate: 800, strong: 1000, very_strong: 1250, elite: 1500)
- Gradient-aware efficiency curve (optimal range: 6-12% gradient, scales from 95% to 100% efficiency)
- See `CLIMBING_MODEL.md` for full documentation

### Fatigue Model
- Effort-based calculation: `effort_km = distance_km + ascent_m/100 + descent_m/200`
- Fitness levels: untrained, recreational, trained, elite
- Fatigue Onset Point (FOP) varies by fitness level (25-75 km-effort)
- See `FATIGUE_MODEL.md` for full documentation

### Terrain Difficulty
- 7 terrain types: road, smooth_trail, dirt_road, rocky_runnable, technical, very_technical, scrambling
- Gradient scaling amplifies difficulty
- Skill adjustment: novice to expert reduces terrain penalties
- See `TERRAIN_DIFFICULTY.md` for full documentation

## Version Management & Cache Busting

### APP_VERSION System

**CRITICAL**: RaceCraft implements a robust cache busting and client state versioning system to ensure users always see the latest code after deployments.

#### Backend Version Management

**Location**: `app.py` lines 163-181

The version is managed in two ways:
1. **From docstring** (default): Extracted from the module docstring at the top of `app.py`
   ```python
   """
   RaceCraft - Fuel & Pacing Planner
   Version: v1.6.1
   Release Date: Feb 05, 2026
   """
   ```

2. **From environment variable** (override): Set `APP_VERSION` in `.env` or Docker environment
   ```bash
   APP_VERSION=v1.7.0
   ```

The version is automatically:
- Logged on app startup
- Passed to all template contexts (`app_version` variable)
- Used to generate cache-busting query strings on static assets

#### Frontend Integration

**Location**: All HTML templates (`templates/*.html`)

Version is injected into HTML templates:
```html
<!-- CSS with cache busting -->
<link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}?v={{ app_version }}">

<!-- JavaScript with cache busting -->
<script src="{{ url_for('static', filename='js/app.js') }}?v={{ app_version }}"></script>

<!-- Global version variables -->
<script>
    window.APP_VERSION = '{{ app_version }}';
    window.CLIENT_STORAGE_VERSION = 'v1.6.1'; // Update when localStorage schema changes
</script>
```

#### Client Storage Versioning

**Location**: `static/js/app.js` lines 3-120

The frontend checks for version mismatches on every page load:
- Compares stored version in `localStorage` with current `CLIENT_STORAGE_VERSION`
- On mismatch: clears localStorage (except Supabase auth tokens) and reinitializes
- Shows user-friendly notification: "✓ App updated to latest version"
- Prevents old saved UI state from breaking new logic

#### Service Worker Management

**Location**: `static/js/app.js` lines 14-28

Automatically unregisters any legacy Service Workers on page load to prevent stale caching layers.

### When to Update Versions

**UPDATE BOTH when releasing**:

1. **APP_VERSION** (in `app.py` docstring):
   - Update for **every release** (major, minor, or patch)
   - Format: `v{major}.{minor}.{patch}` (e.g., v1.7.0)
   - Also update "Release Date" in the docstring
   - This controls cache busting for all static assets

2. **CLIENT_STORAGE_VERSION** (in HTML templates):
   - Update when localStorage/sessionStorage schema changes
   - Update when saved UI state structure changes
   - Update when removing/renaming stored keys
   - Usually matches APP_VERSION, but can lag if storage schema is unchanged
   - Located in: `templates/index.html`, `templates/about.html`, `templates/docs.html`

### Release Checklist

When preparing a new release:

```bash
# 1. Update version in app.py docstring
# Edit app.py lines 1-10 to update:
#   Version: v1.X.X
#   Release Date: MMM DD, YYYY

# 2. Update CLIENT_STORAGE_VERSION if localStorage schema changed
# Edit templates/index.html, about.html, docs.html:
#   window.CLIENT_STORAGE_VERSION = 'v1.X.X';

# 3. (Optional) Set APP_VERSION env var for Docker builds
# Add to .github/workflows/docker-publish.yml if needed:
#   APP_VERSION=${{ github.ref_name }}

# 4. Test locally
python app.py
# Check browser console for version logs

# 5. Commit changes
git add app.py templates/*.html
git commit -m "chore: bump version to v1.X.X"

# 6. Tag release
git tag -a v1.X.X -m "Release v1.X.X"
git push origin v1.X.X
```

### Cache Headers

**Location**: `app.py` lines 180-186

WhiteNoise is configured with:
- **Development**: `max_age=0` (no caching)
- **Production**: `max_age=31536000` (1 year) - safe because of version query strings

This ensures:
- Dev: Always fresh assets during development
- Prod: Aggressive caching with version-based invalidation

### Troubleshooting Cache Issues

If users report seeing old UI after deployment:

1. **Check version is updating**:
   - Verify APP_VERSION in app.py docstring is updated
   - Check browser console logs show correct version
   - Inspect page source to confirm `?v=` query strings

2. **Force localStorage clear**:
   - Increment CLIENT_STORAGE_VERSION in templates
   - Redeploy - users will auto-clear on next visit

3. **Hard refresh in browser**:
   - Chrome/Firefox: Ctrl+Shift+R (Cmd+Shift+R on Mac)
   - Safari: Cmd+Option+R

4. **Check Docker image**:
   - Ensure correct Docker tag is deployed
   - Verify environment variables are set correctly

### Example: Version Mismatch Flow

```
User visits app with old cached JS (v1.5.0)
↓
Browser loads index.html with new version (v1.6.1)
↓
app.js initializes, runs initializeCacheBusting()
↓
Detects version mismatch: stored=v1.5.0, current=v1.6.1
↓
Clears localStorage (preserves Supabase auth)
↓
Shows notification: "✓ App updated to latest version"
↓
User sees fresh UI with correct functionality
```

## Boundaries & Constraints

### Never Do
- **Never commit secrets or API keys** - use environment variables
- **Never modify generated files** in `static/uploads/` or `saved_plans/` manually
- **Never break the API contract** - maintain backward compatibility or document breaking changes
- **Never remove or modify the existing documentation** (FATIGUE_MODEL.md, CLIMBING_MODEL.md, TERRAIN_DIFFICULTY.md) without updating dependent code
- **Never add heavy frontend frameworks** (React, Vue, Angular) - keep it lightweight with vanilla JS
- **Never add unnecessary dependencies** - keep the project lean and maintainable
- **Never deploy without updating APP_VERSION** - prevents cache issues

### Always Do
- **Always test changes locally** before committing
- **Always validate GPX parsing** with different GPX file formats
- **Always maintain Docker compatibility** - test Docker builds after changes
- **Always update documentation** when changing models or calculations
- **Always use secure file handling** for GPX uploads (use `secure_filename` from werkzeug)
- **Always handle edge cases** in calculations (zero distance, missing data, etc.)
- **Always update APP_VERSION on release** - critical for cache busting
- **Always update CLIENT_STORAGE_VERSION when localStorage schema changes**

## API Endpoints

Main endpoints to be aware of:
- `POST /api/upload-gpx` - Upload and parse GPX file
- `POST /api/calculate` - Calculate race plan with pacing and nutrition
- `POST /api/save-plan` - Save race plan to JSON file
- `GET /api/list-plans` - List all saved plans
- `GET /api/load-plan/<filename>` - Load a specific saved plan
- `DELETE /api/delete-plan/<filename>` - Delete a saved plan
- `POST /api/export-plan` - Export race plan to JSON format
- `POST /api/import-plan` - Import race plan from JSON
- `POST /api/export-csv` - Export race plan to CSV format
- `POST /api/export-pdf` - Export race plan to PDF format

## Deployment

### Docker Hub Publishing
- Automated via GitHub Actions workflow (`.github/workflows/docker-publish.yml`)
- Triggered on GitHub release publication
- Images tagged with version and `latest`
- Requires `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` secrets

### Production Considerations
- Use `FLASK_ENV=production` and `FLASK_DEBUG=0`
- Consider reverse proxy (nginx/Traefik) for SSL/TLS
- Configure resource limits in Docker Compose
- Set up health checks for monitoring
- **Always verify APP_VERSION is correct after deployment**

## Common Development Patterns

### Adding a New API Endpoint
1. Add route handler in `app.py`
2. Update frontend JavaScript in `static/js/app.js`
3. Test locally with different input scenarios
4. Update API documentation in README.md if public-facing

### Modifying Calculations
1. Review relevant documentation (FATIGUE_MODEL.md, CLIMBING_MODEL.md, etc.)
2. Update calculation functions in `app.py`
3. Update test script if applicable (`test_climbing_model.py`)
4. Test with various input scenarios
5. Update documentation to reflect changes

### Working with GPX Files
- Use `xml.etree.ElementTree` for parsing
- Handle both `<trkpt>` (track points) and `<rtept>` (route points)
- Validate elevation data presence
- Calculate distances using Haversine formula
- Use `secure_filename()` for file storage

### Updating Application Version
1. Edit `app.py` docstring to update version and release date
2. If localStorage schema changed, update `CLIENT_STORAGE_VERSION` in all HTML templates
3. Update changelog in `app.py` docstring with major changes
4. Test locally to verify version appears in browser console
5. Commit changes with appropriate version tag
6. Create GitHub release to trigger Docker build

## Version History

- **v1.6.1** (Feb 05, 2026)
  - Terminology update: Renamed "Gels/Sachets" to "Servings"
  - About page with markdown content and navigation menu
  - Target time validation bug fix
  - PDF export improvements
  - Elevation profile linear scale with bounded range

- **v1.6.0-target-time-mode**
  - New Target Time Mode: Plan by desired finish time
  - Limit checkpoints to 30 for performance
  - Distance column shows accumulated distance

- **v1.5.3**
  - Documentation organization improvements

- **v1.5.0-load-known-races**
  - Display loaded plan name in UI
  - Clear form on sign-out
  - Manual import for local plans
  - Anonymous user plan support

- **v1.4.1**
  - Supabase initialization improvements
  - Input clearing on GPX load/sign-out

- **v1.4.0**
  - Supabase integration for authentication

## Additional Resources

- **Flask Documentation**: https://flask.palletsprojects.com/
- **Docker Documentation**: https://docs.docker.com/
- **GPX Format Specification**: https://www.topografix.com/gpx.asp
- **WhiteNoise Documentation**: http://whitenoise.evans.io/

---

**Last Updated**: Feb 06, 2026
**Maintained by**: @lennon101 and GitHub Copilot
