# Race Fuel & Pacing Planner - Web Application

A web-based ultra-running race planner that calculates personalized pacing, fuel requirements, and hydration needs based on GPX route files.

## Features

- 🗺️ **GPX Route Upload**: Drag and drop your race route
- ⚡ **Real-time Calculations**: Results update as you adjust parameters
- 💾 **Save/Load Plans**: Store multiple race plans for different events
- 📊 **Interactive Results**: Visual summary cards and detailed segment breakdown
- 📥 **CSV Export**: Download your race plan for offline use
- 🎯 **Time of Day**: Optional race start time to see checkpoint arrival times
- 🎨 **Modern UI**: Clean, responsive interface that works on all devices

## Quick Start

### Option 1: Run Locally

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application:**
   ```bash
   python app.py
   ```

3. **Open your browser:**
   Navigate to `http://localhost:5000`

### Option 2: Docker

1. **Build and run:**
   ```bash
   docker-compose up -d
   ```

2. **Access the app:**
   Navigate to `http://localhost:5000`

3. **View logs:**
   ```bash
   docker-compose logs -f
   ```

4. **Stop the app:**
   ```bash
   docker-compose down
   ```

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

- `POST /api/upload-gpx` - Upload and parse GPX file
- `POST /api/calculate` - Calculate race plan
- `POST /api/save-plan` - Save race plan
- `GET /api/list-plans` - List all saved plans
- `GET /api/load-plan/<filename>` - Load a specific plan
- `DELETE /api/delete-plan/<filename>` - Delete a plan
- `POST /api/export-csv` - Export race plan to CSV

## Configuration

### Constants (in app.py)

```python
ELEVATION_GAIN_FACTOR = 6.0      # Seconds per meter of elevation gain
FATIGUE_MULTIPLIER = 2.0         # Percent pace slowdown per hour
MAX_DOWNHILL_SPEED_INCREASE = 20.0  # Max % pace increase on downhills
DEFAULT_CARBS_PER_HOUR = 60.0    # Default carb intake (grams/hour)
DEFAULT_WATER_PER_HOUR = 500.0   # Default water intake (mL/hour)
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
   - Adjust elevation gain factor if needed
   - Optionally set race start time for time-of-day display

4. **Configure Nutrition**
   - Set target carbs per hour
   - Set target water per hour

5. **Calculate**
   - Click "Calculate Race Plan"
   - Results update in real-time as you adjust values

6. **Save/Export**
   - Save plan for future reference
   - Export to CSV for offline use

## Docker Deployment

### Network Access

To access from other devices on your network:
1. Find your machine's IP address
2. Navigate to `http://YOUR_IP:5000` from any device

### Persistent Storage

The Docker setup uses volumes to persist:
- Uploaded GPX files: `./static/uploads`
- Saved race plans: `./saved_plans`

### Production Deployment

For production, consider:
1. Change `debug=True` to `debug=False` in `app.py`
2. Use a production WSGI server (gunicorn):
   ```dockerfile
   CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
   ```
3. Add environment variables for configuration
4. Set up reverse proxy (nginx) for SSL/TLS

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
```bash
# Rebuild from scratch
docker-compose down
docker-compose build --no-cache
docker-compose up
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

## Credits

Built with:
- Flask (Python web framework)
- Vanilla JavaScript (no frameworks)
- CSS Grid & Flexbox (modern layouts)
