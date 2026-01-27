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
- 7 terrain types: road, smooth_trail, technical_trail, rocky, very_rocky, boulders, scrambling
- Gradient scaling amplifies difficulty
- Skill adjustment: novice to expert reduces terrain penalties
- See `TERRAIN_DIFFICULTY.md` for full documentation

## Boundaries & Constraints

### Never Do
- **Never commit secrets or API keys** - use environment variables
- **Never modify generated files** in `static/uploads/` or `saved_plans/` manually
- **Never break the API contract** - maintain backward compatibility or document breaking changes
- **Never remove or modify the existing documentation** (FATIGUE_MODEL.md, CLIMBING_MODEL.md, TERRAIN_DIFFICULTY.md) without updating dependent code
- **Never add heavy frontend frameworks** (React, Vue, Angular) - keep it lightweight with vanilla JS
- **Never add unnecessary dependencies** - keep the project lean and maintainable

### Always Do
- **Always test changes locally** before committing
- **Always validate GPX parsing** with different GPX file formats
- **Always maintain Docker compatibility** - test Docker builds after changes
- **Always update documentation** when changing models or calculations
- **Always use secure file handling** for GPX uploads (use `secure_filename` from werkzeug)
- **Always handle edge cases** in calculations (zero distance, missing data, etc.)

## API Endpoints

Main endpoints to be aware of:
- `POST /api/upload-gpx` - Upload and parse GPX file
- `POST /api/calculate` - Calculate race plan with pacing and nutrition
- `POST /api/save-plan` - Save race plan to JSON file
- `GET /api/list-plans` - List all saved plans
- `GET /api/load-plan/<filename>` - Load a specific saved plan
- `DELETE /api/delete-plan/<filename>` - Delete a saved plan
- `POST /api/export-csv` - Export race plan to CSV format

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

## Version History

- **v1.0.0-climbing-model-overhaul** (Jan 27, 2026)
  - Vertical speed climbing model (600-1500 m/h)
  - Gradient-aware efficiency curve
  - Improved fatigue model for ultra-distance realism
  - BREAKING CHANGE: `climbing_ability` replaces `elev_gain_factor`

## Additional Resources

- **Flask Documentation**: https://flask.palletsprojects.com/
- **Docker Documentation**: https://docs.docker.com/
- **GPX Format Specification**: https://www.topografix.com/gpx.asp
