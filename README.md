<p align="center">
  <img src="static/logo-header.png" alt="RaceCraft Logo" width="800">
</p>

# RaceCraft - Fuel & Pacing Planner

A web-based race planner for athletes needing to estimate their pacing, checkpoint timings, fuel requirements, and hydration needs. 

## Features

- **GPX Route Upload**: Drag and drop your race route
- **Advanced Fatigue Model**: Effort-based, fitness-dependent fatigue calculation ([learn more](FATIGUE_MODEL.md))
- **Terrain Difficulty System**: Sophisticated trail surface modelling with skill adjustment ([learn more](TERRAIN_DIFFICULTY.md))
- **User Authentication**: Optional Supabase-powered authentication for secure data management
  - Anonymous access for low-friction use
  - Seamless upgrade from anonymous to authenticated account
  - Secure data isolation per user
  - Multi-device sync for authenticated users
- **Real-time Calculations**: Results update as you adjust parameters
- **Save/Load Plans**: Store multiple race plans for different events
- **Interactive Results**: Visual summary cards and detailed segment breakdown
- **CSV Export**: Download your race plan for offline use
- **Time of Day**: Optional race start time to see checkpoint arrival times
- **Modern UI**: Clean, responsive interface that works on all devices

## Quick Start

### Option 1: Docker Compose (Recommended)

1. **Create a `docker-compose.yml` file:**
   ```yaml
   version: '3.8'

   services:
     fuel-planner:
       image: lennon101/racecraft:latest
       container_name: racecraft
       ports:
         - "5000:5000"
       volumes:
         - racecraft-data:/app/data
       environment:
         - FLASK_ENV=development
         - FLASK_DEBUG=1
         - UPLOAD_FOLDER=/app/data/uploads
         - SAVED_PLANS_FOLDER=/app/data/saved_plans
       restart: unless-stopped
       networks:
         - racecraft

   volumes:
     racecraft-data:

   networks:
     racecraft:
   ```

2. **Pull and run the container:**
   ```bash
   docker compose up -d
   ```

3. **Access the application:**
   Open your browser to `http://localhost:5000`

### Option 2: Docker Run

1. **Pull the image:**
   ```bash
   docker pull lennon101/racecraft:latest
   ```

2. **Create a volume for persistent data:**
   ```bash
   docker volume create racecraft-data
   ```

3. **Run the container:**
   ```bash
   docker run -d \
     --name racecraft \
     -p 5000:5000 \
     -v racecraft-data:/app/data \
     -e UPLOAD_FOLDER=/app/data/uploads \
     -e SAVED_PLANS_FOLDER=/app/data/saved_plans \
     --restart unless-stopped \
     lennon101/racecraft:latest
   ```

4. **Access the application:**
   Open your browser to `http://localhost:5000`

### Option 3: Railway Deployment

Deploy directly from GitHub to Railway.app with one click:

1. **Connect to Railway:**
   - Go to [Railway.app](https://railway.app)
   - Create a new project from GitHub repo
   - Select the `lennon101/RaceCraft` repository

2. **Automatic Deployment:**
   - Railway detects Python automatically
   - Uses `Procfile` for gunicorn configuration
   - Static files served via WhiteNoise middleware

3. **Access your app:**
   - Railway provides a public URL
   - App deploys automatically on each commit

For detailed Railway deployment instructions, see [RAILWAY_DEPLOYMENT.md](RAILWAY_DEPLOYMENT.md).

### Option 4: Run Locally (Development)

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd Fuel-Plan-Tool
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python app.py
   ```

4. **Open your browser:**
   Navigate to `http://localhost:5001` (dev server uses port 5001, Docker uses 5000)

## Authentication Setup (Optional)

RaceCraft supports optional Supabase authentication for secure user data management and multi-device sync. The app works in two modes:

- **Legacy Mode (Default)**: No authentication required. Plans are stored locally or in file-based storage.
- **Authenticated Mode**: Supabase-powered authentication with secure data isolation and multi-device sync.

### Anonymous Users

By default, users can access RaceCraft without signing up:
- A temporary anonymous session is created automatically
- Plans can be saved and accessed during the session
- Data persists locally in the browser
- Gentle prompts encourage account creation for multi-device access

### Setting Up Authentication

1. **Create a Supabase project** at [supabase.com](https://supabase.com)

2. **Run the database migration**:
   - Go to your Supabase project dashboard
   - Navigate to **SQL Editor**
   - Run the SQL script from `supabase/migrations/001_create_user_plans.sql`
   - See [supabase/SETUP.md](supabase/SETUP.md) for detailed instructions

3. **Configure environment variables**:
   ```bash
   # Create a .env file or set environment variables
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_ANON_KEY=your_anon_key_here
   SUPABASE_SERVICE_KEY=your_service_key_here
   ```

4. **Deploy with Docker Compose**:
   ```yaml
   services:
     fuel-planner:
       image: lennon101/racecraft:latest
       environment:
         - SUPABASE_URL=https://your-project.supabase.co
         - SUPABASE_ANON_KEY=your_anon_key
         - SUPABASE_SERVICE_KEY=your_service_key
         - FLASK_ENV=production
   ```

5. **Restart the application** - authentication will be automatically enabled

### Authentication Features

- **Email + Password**: Traditional sign up and sign in
- **Magic Links**: Passwordless email authentication
- **Anonymous Migration**: Existing anonymous plans are automatically migrated when creating an account
- **Data Security**: Row Level Security (RLS) ensures users can only access their own data
- **Multi-Device Sync**: Access your plans from any device when authenticated

For complete setup instructions, see [supabase/SETUP.md](supabase/SETUP.md).

## Project Structure

```
Fuel-Plan-Tool/
├── app.py                 # Flask backend API
├── requirements.txt       # Python dependencies
├── Dockerfile            # Docker configuration
├── docker-compose.yml    # Docker Compose setup
├── Fuel-Plan.py          # Original CLI script (kept for reference)
├── templates/
│   └── index.html        # Main HTML page
├── static/
│   ├── css/
│   │   └── style.css     # Styles
│   ├── js/
│   │   └── app.js        # Frontend JavaScript
│   └── uploads/          # GPX file storage
└── saved_plans/          # Saved race plans (JSON)
```

## API Endpoints

### Race Planning
- `POST /api/upload-gpx` - Upload and parse GPX file
- `POST /api/calculate` - Calculate race plan
- `POST /api/export-csv` - Export race plan to CSV

### Plan Management
- `POST /api/save-plan` - Save race plan (supports both authenticated and anonymous users)
- `GET /api/list-plans` - List all saved plans (filtered by user ownership)
- `GET /api/load-plan/<filename>` - Load a specific plan (with ownership verification)
- `DELETE /api/delete-plan/<filename>` - Delete a plan (with ownership verification)
- `POST /api/export-plan` - Export plan as JSON
- `POST /api/import-plan` - Import plan from JSON

### Authentication (when Supabase is configured)
- `GET /api/auth/check` - Check if authentication is enabled
- `POST /api/auth/migrate` - Migrate anonymous plans to authenticated account

## Configuration

### Fatigue Model

RaceCraft uses an advanced **effort-based fatigue model** that accounts for cumulative effort, fitness level, and delayed fatigue onset. See [FATIGUE_MODEL.md](FATIGUE_MODEL.md) for complete documentation.

**Key parameters:**
- **Fitness Level**: Determines your Fatigue Onset Point (FOP)
  - Untrained: 20-30 km-effort
  - Recreational: 30-45 km-effort
  - Trained: 45-65 km-effort
  - Elite: 65-85+ km-effort
- **Effort Calculation**: `effort_km = distance_km + ascent_m/100 + descent_m/200`
- **Fatigue Formula**: `fatigue_multiplier = 1 + α × ((E − FOP) / FOP)^β`

### Terrain Difficulty Model

RaceCraft models terrain difficulty as a **local efficiency penalty** that slows pace without affecting fatigue accumulation. See [TERRAIN_DIFFICULTY.md](TERRAIN_DIFFICULTY.md) for complete documentation.

**Key features:**
- **7 Terrain Types**: Road (0.95×) to Scrambling (2.0×)
- **Gradient Scaling**: Steeper terrain amplifies difficulty
- **Skill Adjustment**: Technical proficiency reduces terrain penalties
- **Descent Weighting**: 100% effect downhill, 70% uphill
- **Formula**: `segment_time = base_time × terrain_factor × fatigue_multiplier`

### Constants (in app.py)

```python
ELEVATION_GAIN_FACTOR = 6.0      # Seconds per meter of elevation gain
MAX_DOWNHILL_SPEED_INCREASE = 20.0  # Max % pace increase on downhills
DEFAULT_CARBS_PER_HOUR = 60.0    # Default carb intake (grams/hour)
DEFAULT_WATER_PER_HOUR = 500.0   # Default water intake (mL/hour)

# Fitness level parameters
FITNESS_LEVEL_PARAMS = {
    'untrained': {'fop': 25, 'alpha': 0.35, 'beta': 1.8},
    'recreational': {'fop': 37.5, 'alpha': 0.25, 'beta': 1.5},
    'trained': {'fop': 55, 'alpha': 0.20, 'beta': 1.4},
    'elite': {'fop': 75, 'alpha': 0.15, 'beta': 1.3}
}
```

### Port Configuration

To change the port, edit `app.py`:
```python
app.run(host='0.0.0.0', port=5000, debug=True)
```

And update `docker-compose.yml`:
```yaml
ports:
  - "8080:5000"  # host:container
```

## Usage Workflow

1. **Upload GPX Route**
   - Click "Choose GPX file" and select your race route
   - Route information displays automatically

2. **Configure Checkpoints**
   - Set number of checkpoints
   - Enter average stop time at each checkpoint
   - Specify distance to each checkpoint in kilometers

3. **Set Pacing Parameters**
   - Enter your Zone 2 pace (flat ground)
   - Select your fitness level (determines fatigue onset)
   - Adjust elevation gain factor if needed
   - Optionally set race start time for time-of-day display

4. **Configure Terrain Difficulty** (Optional)
   - Enable terrain difficulty adjustments
   - Select terrain type for each segment (road to scrambling)
   - Set your technical skill level (novice to expert)

5. **Configure Nutrition**
   - Set target carbs per hour
   - Set target water per hour

6. **Calculate**
   - Click "Calculate Race Plan"
   - Results update in real-time as you adjust values

7. **Save/Export**
   - Save plan for future reference
   - Export to CSV for offline use

## Docker Deployment

### Image Information

- **Image**: `lennon101/racecraft:latest`
- **Port**: 5000
- **Volumes**: 
  - `racecraft-uploads`: Stores uploaded GPX files
  - `racecraft-plans`: Stores saved race plans (JSON)
  - `racecraft-static`: Static assets cache

### Network Access

To access from other devices on your network:
1. Find your machine's IP address:
   ```bash
   # Windows
   ipconfig | findstr IPv4
   
   # Linux/Mac
   hostname -I
   ```
2. Navigate to `http://YOUR_IP:5000` from any device on the same network

### Managing Containers

**View running containers:**
```bash
docker ps
```

**View logs:**
```bash
docker logs racecraft
# or for live logs
docker logs -f racecraft
```

**Stop the container:**
```bash
docker stop racecraft
```

**Start the container:**
```bash
docker start racecraft
```

**Restart the container:**
```bash
docker restart racecraft
```

**Remove the container:**
```bash
docker stop racecraft
docker rm racecraft
```

### Managing Volumes

**List volumes:**
```bash
docker volume ls
```

**Inspect a volume:**
```bash
docker volume inspect racecraft-uploads
```

**Backup volume data:**
```bash
docker run --rm -v racecraft-plans:/data -v $(pwd):/backup alpine tar czf /backup/racecraft-plans-backup.tar.gz -C /data .
```

**Restore volume data:**
```bash
docker run --rm -v racecraft-plans:/data -v $(pwd):/backup alpine tar xzf /backup/racecraft-plans-backup.tar.gz -C /data
```

### Updating the Application

**With Docker Compose:**
```bash
docker compose pull
docker compose up -d
```

**With Docker Run:**
```bash
docker pull lennon101/racecraft:latest
docker stop racecraft
docker rm racecraft
# Then run the docker run command again
```

### Production Deployment

For production environments:

1. **Use Docker Compose** with environment-specific configuration:
   ```yaml
   environment:
     - FLASK_ENV=production
     - FLASK_DEBUG=0
   ```

2. **Set up a reverse proxy** (nginx/Traefik) for:
   - SSL/TLS termination
   - Domain routing
   - Load balancing

3. **Configure resource limits:**
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '0.5'
         memory: 512M
   ```

4. **Enable health checks:**
   ```yaml
   healthcheck:
     test: ["CMD", "curl", "-f", "http://localhost:5000"]
     interval: 30s
     timeout: 10s
     retries: 3
   ```

## Browser Compatibility

- Chrome/Edge: Full support
- Firefox: Full support
- Safari: Full support
- Mobile browsers: Responsive design

## Troubleshooting

### Port Already in Use
```bash
# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :5000
kill -9 <PID>
```

### Docker Issues

**Rebuild from scratch:**
```bash
docker compose down -v
docker compose pull
docker compose up -d
```

**Check container status:**
```bash
docker ps -a
docker logs racecraft
```

**Port conflicts:**
```bash
# Windows - check what's using port 5000
netstat -ano | findstr :5000

# Linux/Mac
lsof -i :5000
```

**Clean up Docker resources:**
```bash
# Remove stopped containers
docker container prune

# Remove unused volumes
docker volume prune

# Remove unused images
docker image prune
```

### GPX Upload Fails
- Ensure file is valid GPX format
- Check file size (max 16MB)
- Verify file contains track or route points

## Development

### Run in Debug Mode
```bash
python app.py
```
Changes to Python code require restart. HTML/CSS/JS changes refresh automatically in browser.

### Add New Features
1. Backend: Add route in `app.py`
2. Frontend: Update `app.js` and `index.html`
3. Styling: Modify `style.css`

## Original CLI Version

The original command-line script (`Fuel-Plan.py`) is still available and fully functional. Run it with:
```bash
python Fuel-Plan.py
```

## License

Free to use and modify for personal use.

## About RaceCraft

RaceCraft is your comprehensive race planning companion, helping endurance athletes optimise their performance through data-driven pacing and fuelling strategies.

## Credits

Built with:
- Flask (Python web framework)
- Vanilla JavaScript (no frameworks)
- CSS Grid & Flexbox (modern layouts)
