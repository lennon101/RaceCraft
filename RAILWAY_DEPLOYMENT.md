# Railway Deployment Guide

## Overview

This guide explains how to deploy RaceCraft to Railway directly from the GitHub repository.

## Issue Resolved

**Problem**: When deploying directly from GitHub to Railway, the app would load HTML but buttons wouldn't work (JavaScript/CSS files not loading).

**Root Cause**: Gunicorn (used by Railway for WSGI apps) doesn't serve static files by default in production. Flask's development server serves static files automatically, but production WSGI servers like gunicorn require additional configuration.

**Solution**: WhiteNoise middleware was added to serve static files efficiently in production.

## Files for Railway Deployment

### 1. `Procfile`
Tells Railway how to start the application:
```
web: gunicorn --bind 0.0.0.0:$PORT app:app
```

### 2. `runtime.txt`
Specifies the Python version for Railway:
```
python-3.12.3
```

### 3. `requirements.txt`
Includes WhiteNoise for static file serving:
```
Flask==3.0.0
Werkzeug==3.0.1
gunicorn==21.2.0
whitenoise==6.6.0
```

### 4. `app.py`
WhiteNoise middleware configuration:
```python
from whitenoise import WhiteNoise

app = Flask(__name__)

# Configure WhiteNoise for static file serving in production
app.wsgi_app = WhiteNoise(app.wsgi_app, root='static/', prefix='static/')
```

## Deployment Steps

1. **Connect Repository to Railway**
   - Go to [Railway.app](https://railway.app)
   - Create a new project
   - Select "Deploy from GitHub repo"
   - Choose the `lennon101/RaceCraft` repository

2. **Railway Auto-Detection**
   - Railway will automatically detect this as a Python application
   - It will use `runtime.txt` to set the Python version
   - It will use `Procfile` to start the application with gunicorn

3. **Environment Variables** (Optional)
   - `FLASK_ENV`: Set to `production` for production deployments
   - `FLASK_DEBUG`: Set to `0` for production (default)
   - Railway will automatically set `$PORT`

4. **Deploy**
   - Railway will automatically build and deploy on each push to the main branch
   - The app will be available at the generated Railway URL

## How WhiteNoise Works

WhiteNoise wraps the Flask WSGI application and intercepts requests for static files:

1. Request comes in for `/static/js/app.js`
2. WhiteNoise checks if the file exists in the `static/` directory
3. If found, WhiteNoise serves it directly with appropriate caching headers
4. If not found, the request passes through to Flask

### Benefits
- ✅ No separate web server (nginx) needed for static files
- ✅ Efficient caching with proper HTTP headers
- ✅ Compression support (gzip/brotli)
- ✅ Works seamlessly with Flask's `url_for('static', ...)`
- ✅ Zero configuration needed for basic usage

## Testing the Deployment

After deployment, test that static files are loading:

1. Open the Railway URL in a browser
2. Open Developer Tools (F12)
3. Check the **Network** tab:
   - `/static/js/app.js` should return **200 OK**
   - `/static/css/style.css` should return **200 OK**
4. Check the **Console** tab for any JavaScript errors
5. Test button functionality (upload GPX, calculate, etc.)

## Troubleshooting

### Buttons Still Don't Work
1. Check browser console for 404 errors on static files
2. Verify Railway build logs for any errors
3. Ensure `whitenoise` is in `requirements.txt`
4. Verify the `runtime.txt` Python version matches your local version

### Static Files Return 404
1. Check that `static/` directory exists in the repository
2. Verify WhiteNoise configuration in `app.py`
3. Check Railway build logs for file structure

### App Won't Start
1. Check Railway logs for startup errors
2. Verify `Procfile` syntax is correct
3. Ensure all dependencies are in `requirements.txt`

## Docker vs Railway Deployment

**Docker Deployment** (using `Dockerfile`):
- More control over the environment
- Can include system packages
- Consistent across environments
- Recommended for complex setups

**Railway Direct GitHub Deployment**:
- Simpler setup (no Dockerfile needed)
- Faster initial deployment
- Automatic Python version detection
- Great for standard Flask apps

Both methods work correctly with WhiteNoise for static file serving.

## Additional Resources

- [WhiteNoise Documentation](http://whitenoise.evans.io/)
- [Railway Documentation](https://docs.railway.app/)
- [Flask Production Deployment](https://flask.palletsprojects.com/en/3.0.x/deploying/)
- [Gunicorn Documentation](https://docs.gunicorn.org/)
