# Troubleshooting: Plans Not Saving to Supabase

## Symptom
You see "Plan updated successfully!" but no rows appear in the Supabase `user_plans` table.

## Root Cause
The application is silently falling back to file-based storage instead of using Supabase. This happens when:
1. **`SUPABASE_SERVICE_KEY` environment variable is not set** (most common)
2. The admin client cannot connect to Supabase
3. There's a network or authentication issue with Supabase

## Quick Diagnosis

### Step 1: Check Startup Logs
When the application starts, look for these messages in the logs:

✅ **Good configuration:**
```
✓ Supabase credentials loaded - authentication enabled
  URL: https://xxxxx.supabase.co
  Anon key: eyJhb...
  Service key: eyJhb...
  ✓ Authenticated user database operations enabled
```

❌ **Missing service key:**
```
✓ Supabase credentials loaded - authentication enabled
  URL: https://xxxxx.supabase.co
  Anon key: eyJhb...
  ⚠ WARNING: SUPABASE_SERVICE_KEY not set!
  ⚠ Authenticated users will NOT be able to save plans to database
  ⚠ Set SUPABASE_SERVICE_KEY environment variable to fix this
```

### Step 2: Use the Diagnostic Endpoint
Access this URL in your browser or with curl:
```
https://your-app-url/api/auth/diagnose
```

You should see output like:
```json
{
  "supabase_enabled": true,
  "supabase_url_set": true,
  "supabase_anon_key_set": true,
  "supabase_service_key_set": true,  ← Should be true
  "supabase_import_available": true,
  "anon_client_initialized": false,
  "admin_client_initialized": false,
  "anon_client_available": true,
  "admin_client_available": true,  ← Should be true
  "admin_client_connection": "success",  ← Should be "success"
  "user_plans_table_accessible": true  ← Should be true
}
```

**Key fields to check:**
- `supabase_service_key_set`: Must be `true`
- `admin_client_available`: Must be `true`
- `admin_client_connection`: Must be `"success"`
- `user_plans_table_accessible`: Must be `true`

### Step 3: Try Saving Again
After checking diagnostics, try saving a plan. Check the backend logs for:

✅ **Success:**
```
✓ Updated plan 'My Plan' for user abc-123-def
```
or
```
✓ Inserted new plan 'My Plan' for user abc-123-def
```

❌ **Failure:**
```
ERROR: Supabase admin client not available. SUPABASE_SERVICE_KEY may not be set.
```
or
```
Supabase save error: [detailed error message]
[stack trace]
```

## Solutions

### Solution 1: Set SUPABASE_SERVICE_KEY (Most Common)

The `SUPABASE_SERVICE_KEY` is required for authenticated users to save plans. 

#### Get Your Service Key
1. Go to your Supabase project dashboard
2. Navigate to **Settings** → **API**
3. Find the **service_role key** (starts with `eyJ...`)
4. ⚠️ **Keep this secret!** Never commit it to version control

#### Set the Environment Variable

**For Docker Compose:**
```yaml
services:
  racecraft:
    image: lennon101/racecraft:latest
    environment:
      - SUPABASE_URL=https://your-project.supabase.co
      - SUPABASE_ANON_KEY=your_anon_key
      - SUPABASE_SERVICE_KEY=your_service_key  # Add this
      - FLASK_ENV=production
```

**For Docker Run:**
```bash
docker run -d \
  -e SUPABASE_URL=https://your-project.supabase.co \
  -e SUPABASE_ANON_KEY=your_anon_key \
  -e SUPABASE_SERVICE_KEY=your_service_key \
  -e FLASK_ENV=production \
  -p 5000:5000 \
  lennon101/racecraft:latest
```

**For Railway/Render/Other Platform:**
1. Go to your deployment platform's environment variable settings
2. Add a new variable:
   - Name: `SUPABASE_SERVICE_KEY`
   - Value: Your service role key from Supabase
3. Redeploy the application

**For Local Development (.env file):**
```bash
# .env file
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key_here
SUPABASE_SERVICE_KEY=your_service_key_here  # Add this line
```

#### Verify the Fix
After setting the variable:
1. Restart/redeploy the application
2. Check startup logs for the success message
3. Access `/api/auth/diagnose` to verify configuration
4. Try saving a plan
5. Check Supabase dashboard for the row

### Solution 2: Check Supabase Connection

If the service key is set but plans still don't save:

**Check network connectivity:**
```bash
# From your deployment environment, test connection
curl https://your-project.supabase.co
```

**Check Supabase project status:**
- Go to Supabase dashboard
- Verify project is not paused or suspended
- Check for any service outages

**Verify database migration was run:**
```sql
-- Run in Supabase SQL Editor
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name = 'user_plans';
```
Should return one row. If not, run the migration from `supabase/migrations/001_create_user_plans.sql`.

### Solution 3: Check RLS Policies

**Verify Row Level Security policies exist:**
```sql
-- Run in Supabase SQL Editor
SELECT schemaname, tablename, policyname 
FROM pg_policies 
WHERE tablename = 'user_plans';
```

Should return multiple policies. If not, run the migration script.

**Test admin access directly:**
```sql
-- Using service role key in Supabase dashboard
SELECT * FROM user_plans LIMIT 1;
```
Should work without errors.

## Detailed Error Messages

### Error: "Supabase admin client not available"
**Cause:** `SUPABASE_SERVICE_KEY` is not set or invalid
**Fix:** Set the environment variable with your service role key

### Error: "Failed to save plan to database: [error]"
**Cause:** Various Supabase connection or permission issues
**Fix:** Check the detailed error message in the logs and:
- Verify network connectivity
- Check Supabase project status
- Verify RLS policies are correct
- Check service key is valid

### No Error, But Plans in File System
**Symptom:** Plans save successfully but appear in file system, not Supabase
**Cause:** Error is being caught and handled silently (older version)
**Fix:** Update to latest version with improved error handling

## Verification Checklist

After applying fixes, verify:

- [ ] Startup logs show service key is set
- [ ] `/api/auth/diagnose` shows all checks passing
- [ ] Can save a plan without errors
- [ ] Plan appears in Supabase `user_plans` table with `owner_id` set
- [ ] Can load the plan successfully
- [ ] Backend logs show "✓ Inserted new plan" or "✓ Updated plan"

## SQL Queries for Verification

**Check if plans are being saved:**
```sql
SELECT 
    id,
    owner_id,
    plan_name,
    created_at,
    updated_at
FROM user_plans
WHERE owner_id IS NOT NULL
ORDER BY created_at DESC
LIMIT 10;
```

**Check your specific user's plans:**
```sql
-- Replace USER_ID with your actual user ID
SELECT 
    id,
    plan_name,
    created_at,
    updated_at
FROM user_plans
WHERE owner_id = 'USER_ID'
ORDER BY created_at DESC;
```

**Count total plans by type:**
```sql
SELECT 
    CASE 
        WHEN owner_id IS NOT NULL THEN 'Authenticated'
        WHEN anonymous_id IS NOT NULL THEN 'Anonymous'
        ELSE 'Invalid'
    END AS user_type,
    COUNT(*) as plan_count
FROM user_plans
GROUP BY user_type;
```

## Still Not Working?

If you've tried all the above and plans still aren't saving:

1. **Check application logs** for detailed error messages
2. **Enable debug logging** by setting `FLASK_DEBUG=1`
3. **Check browser console** for frontend errors
4. **Verify JWT token** is being sent in requests (Network tab in DevTools)
5. **Check Supabase logs** in the dashboard under Logs & Reports

### Getting More Help

When reporting issues, include:
1. Output from `/api/auth/diagnose` endpoint
2. Startup logs from the application
3. Any error messages from backend logs
4. Output from browser console (F12 → Console)
5. Which deployment platform you're using
6. Whether the issue is for authenticated users, anonymous users, or both

## Summary

**Most common fix:** Set the `SUPABASE_SERVICE_KEY` environment variable and redeploy.

The diagnostic endpoint and improved logging will help identify exactly what's wrong so you can fix it quickly.
