# Cache Busting & Client State Versioning

## Overview

RaceCraft implements a comprehensive cache busting and client state versioning system to ensure users always see the latest frontend code after deployments. This prevents the common "works in incognito mode only" issue where browsers cache stale JavaScript/CSS files.

## Problem This Solves

After deploying new Docker image versions on Railway (or other platforms), users would experience:
- UI appearing stale or partially broken
- Backend updated but frontend JS/CSS outdated
- Issues persisting in normal browser sessions
- Problems only resolving in incognito mode

This indicated persistent client-side caching issues that survived deployments and caused version mismatches between frontend and backend.

## Multi-Layered Solution

### 1. Static Asset Cache Busting

**What**: All JS and CSS assets include version-based query strings
**Example**: `app.js?v=v1.6.1`, `style.css?v=v1.6.1`

**Implementation**:
- Backend extracts version from `app.py` docstring or `APP_VERSION` env var
- Version passed to all template contexts
- Flask templates use: `{{ url_for('static', filename='js/app.js') }}?v={{ app_version }}`

**Result**: Browsers fetch updated assets automatically when version changes

### 2. Frontend Version Injection

**What**: Version information injected as global JavaScript variables

**Implementation** (in all HTML templates):
```html
<script>
    window.APP_VERSION = '{{ app_version }}';
    window.CLIENT_STORAGE_VERSION = 'v1.6.1';
</script>
```

**Result**: Frontend can detect version and log to console for debugging

### 3. Client Storage Versioning

**What**: Automatic localStorage version checking and migration

**Implementation** (`static/js/app.js`):
```javascript
function checkClientStorageVersion() {
    const currentVersion = window.CLIENT_STORAGE_VERSION || window.APP_VERSION;
    const storedVersion = localStorage.getItem('racecraft_storage_version');
    
    if (storedVersion && storedVersion !== currentVersion) {
        // Version mismatch - clear old state
        // Preserve Supabase auth tokens
        // Set new version
        // Show notification
    }
}
```

**Result**: Old saved UI state cannot silently break new logic

### 4. Service Worker Safety

**What**: Automatic unregistration of any legacy Service Workers

**Implementation** (`static/js/app.js`):
```javascript
function unregisterServiceWorkers() {
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.getRegistrations().then(registrations => {
            registrations.forEach(reg => reg.unregister());
        });
    }
}
```

**Result**: No invisible caching layer survives deploys

### 5. Production Cache Headers

**What**: Aggressive caching with version-based invalidation

**Implementation** (`app.py`):
```python
app.wsgi_app = WhiteNoise(
    app.wsgi_app,
    root='static/',
    prefix='static/',
    max_age=0 if os.environ.get('FLASK_ENV') == 'development' else 31536000
)
```

**Result**: 
- Dev: No caching for rapid iteration
- Prod: 1-year cache safe because version query strings invalidate

## Version Management

### How Versions Are Determined

**Priority order**:
1. `APP_VERSION` environment variable (if set)
2. Extracted from `app.py` docstring `Version: v1.6.1` line
3. Fallback to `'unknown'`

**Example docstring**:
```python
"""
RaceCraft - Fuel & Pacing Planner
Version: v1.6.1
Release Date: Feb 05, 2026
"""
```

### When to Update Versions

**Update `APP_VERSION`** (in `app.py` docstring):
- Every release (major, minor, or patch)
- Format: `v{major}.{minor}.{patch}` (e.g., v1.7.0)
- This invalidates all static asset caches

**Update `CLIENT_STORAGE_VERSION`** (in HTML templates):
- When localStorage/sessionStorage schema changes
- When saved UI state structure changes
- When removing/renaming stored keys
- Usually matches APP_VERSION but can lag if storage unchanged

## Release Workflow

### Before Each Release:

1. **Update app.py docstring**:
   ```python
   """
   RaceCraft - Fuel & Pacing Planner
   Version: v1.7.0  # ← Update this
   Release Date: Feb 06, 2026  # ← Update this
   ```

2. **Update CLIENT_STORAGE_VERSION if needed**:
   Edit `templates/index.html`, `about.html`, `docs.html`:
   ```javascript
   window.CLIENT_STORAGE_VERSION = 'v1.7.0'; // ← Update if storage changed
   ```

3. **Test locally**:
   ```bash
   python app.py
   # Open http://localhost:5000
   # Check browser console for version logs
   ```

4. **Commit and tag**:
   ```bash
   git add app.py templates/*.html
   git commit -m "chore: bump version to v1.7.0"
   git tag -a v1.7.0 -m "Release v1.7.0"
   git push origin v1.7.0
   ```

5. **Verify after deployment**:
   - Check browser console shows new version
   - Verify page source has `?v=v1.7.0` on assets
   - Test localStorage migration if version changed

## User Experience

### What Users See

When a user visits after a version upgrade:

1. **Page loads** with new version injected
2. **Cache busting initializes** immediately (before DOM ready)
3. **Version check** compares stored vs current version
4. **If mismatch**:
   - localStorage cleared (except auth tokens)
   - New version saved
   - Friendly notification appears: "✓ App updated to latest version"
   - Notification auto-fades after 3 seconds

### Console Logging

Every page load shows:
```
==================================================
RaceCraft - Race Fuel & Pacing Planner
==================================================
App Version:     v1.6.1
Storage Version: v1.6.1
User Agent:      Mozilla/5.0...
==================================================
```

If version upgraded:
```
Client storage version mismatch: stored=v1.5.0, current=v1.6.1
Clearing localStorage to prevent compatibility issues...
✓ Client storage upgraded to version v1.6.1
```

## Troubleshooting

### Users Report Old UI After Deployment

**Check**:
1. Is `APP_VERSION` updated in `app.py` docstring?
2. Does browser console show correct version?
3. Does page source have `?v=` query strings on assets?

**Solutions**:
- If version not updated: Update and redeploy
- If CLIENT_STORAGE_VERSION unchanged: Increment it to force localStorage clear
- If browser still shows old: User needs hard refresh (Ctrl+Shift+R)

### How to Force All Users to Refresh

**Option 1**: Increment `CLIENT_STORAGE_VERSION`
- Update in all HTML templates
- Redeploy
- All users will auto-clear localStorage on next visit

**Option 2**: Increment `APP_VERSION`
- Update in `app.py` docstring
- Redeploy
- All static assets will have new cache-busting query strings

### Testing Version Migration Locally

```javascript
// In browser console:

// 1. Set old version
localStorage.setItem('racecraft_storage_version', 'v1.5.0');

// 2. Reload page
location.reload();

// 3. Check console for migration logs
// Should see: "Client storage version mismatch..."
// Should see: "✓ Client storage upgraded to version v1.6.1"
```

## Technical Details

### Files Modified

**Backend**:
- `app.py` - Version extraction, WhiteNoise config, template context

**Frontend**:
- `templates/index.html` - Cache busting, version injection
- `templates/about.html` - Cache busting, version injection
- `templates/docs.html` - Cache busting, version injection
- `static/js/app.js` - Client-side versioning system

**Documentation**:
- `copilot-instructions.md` - Complete version management guide
- `.env.example` - APP_VERSION documentation

### Key Functions

**Backend (`app.py`)**:
- `extract_app_version()` - Gets version from docstring or env var
- `index()`, `about()`, `documentation()` - Pass `app_version` to templates

**Frontend (`static/js/app.js`)**:
- `initializeCacheBusting()` - Main entry point (runs immediately)
- `logVersionInfo()` - Logs version to console
- `unregisterServiceWorkers()` - Removes legacy SW
- `checkClientStorageVersion()` - Version check and migration

### Storage Keys Used

- `racecraft_storage_version` - Current version identifier
- `sb-*` - Supabase auth tokens (preserved during migration)

## Benefits

✅ **Eliminates "works in incognito only" issues**
- Users always get latest code after deployment
- No more stale JavaScript causing errors

✅ **Prevents data corruption**
- Old localStorage structure doesn't break new logic
- Automatic migration on version change

✅ **Improves developer confidence**
- Ship updates without worrying about cache
- Predictable behavior across deployments

✅ **Better debugging**
- Version visible in console
- Clear migration logs
- Easy to verify deployed version

✅ **User-friendly**
- Automatic and invisible
- Friendly notification on upgrade
- Preserves authentication

## Future Enhancements

Possible improvements (currently out of scope):

- Hash-based asset filenames (Webpack/Vite style)
- Automated version bumping in CI/CD
- Version displayed in UI footer
- Client-side version compatibility API endpoint
- Progressive Web App with proper Service Worker

---

**Last Updated**: Feb 06, 2026
**Status**: ✅ Implemented and Production-Ready
