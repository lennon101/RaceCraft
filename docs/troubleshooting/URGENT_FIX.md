# URGENT: Plans Not Saving to Supabase - Quick Fix

## Problem
You're seeing "Plan updated successfully!" but no rows appear in Supabase `user_plans` table.

## Root Cause
Your plans are being saved to the **file system** instead of **Supabase** because the `SUPABASE_SERVICE_KEY` environment variable is not set.

## Quick Fix (5 minutes)

### Step 1: Get Your Service Key
1. Go to [Supabase Dashboard](https://app.supabase.com)
2. Select your project
3. Go to **Settings** → **API**
4. Copy the **service_role key** (starts with `eyJ...`)

### Step 2: Set the Environment Variable

**Choose your deployment method:**

#### Docker Compose
Edit your `docker-compose.yml`:
```yaml
environment:
  - SUPABASE_SERVICE_KEY=your_service_key_here  # Add this line
```

Then restart:
```bash
docker-compose down
docker-compose up -d
```

#### Railway/Render/Vercel
1. Go to your deployment dashboard
2. Find "Environment Variables" or "Settings"
3. Add new variable:
   - **Name:** `SUPABASE_SERVICE_KEY`
   - **Value:** Your service key from Supabase
4. Redeploy or restart the application

#### Docker Run
Add the `-e` flag:
```bash
docker run -d \
  -e SUPABASE_SERVICE_KEY=your_service_key_here \
  [other flags...] \
  lennon101/racecraft:latest
```

### Step 3: Verify the Fix

1. **Check startup logs** - Should now show:
   ```
   ✓ Authenticated user database operations enabled
   ```

2. **Access diagnostic endpoint:**
   ```
   https://your-app-url/api/auth/diagnose
   ```
   
   Should show:
   ```json
   {
     "supabase_service_key_set": true,
     "admin_client_available": true,
     "admin_client_connection": "success"
   }
   ```

3. **Test saving a plan:**
   - Sign in
   - Save a plan
   - Check Supabase dashboard → Table Editor → user_plans
   - You should see a new row with your `owner_id`

## Alternative: Check Current Configuration

Visit this URL to diagnose the issue:
```
https://your-app-url/api/auth/diagnose
```

Look for:
- `supabase_service_key_set`: Should be `true`
- `admin_client_available`: Should be `true`
- `admin_client_connection`: Should be `"success"`

If any are `false` or show errors, you need to set the service key.

## Why This Happened

The previous fix correctly updated the code to use the admin client for authenticated users, but the **service key was never configured in your deployment environment**. Without it, the admin client can't be initialized, causing a silent fallback to file-based storage.

## Security Note

⚠️ **The service role key has full database access. Keep it secret!**
- Never commit it to version control
- Only store it in environment variables
- Don't share it publicly
- It's safe to use server-side (which is what RaceCraft does)

## Complete Documentation

For more detailed information, see:
- **TROUBLESHOOTING.md** - Comprehensive troubleshooting guide
- **FIX_SUMMARY.md** - Technical details of the original fix
- **TESTING_GUIDE.md** - How to test the fix thoroughly

## Still Not Working?

If setting the service key doesn't fix it:

1. Check backend logs for errors
2. Review TROUBLESHOOTING.md for other potential issues
3. Run the diagnostic endpoint and share the output
4. Check Supabase project status (not paused/suspended)

## Summary

**What to do RIGHT NOW:**
1. Get service key from Supabase dashboard (Settings → API)
2. Add `SUPABASE_SERVICE_KEY` environment variable to your deployment
3. Restart/redeploy the application
4. Test saving a plan
5. Verify row appears in Supabase

This should resolve the issue immediately!
