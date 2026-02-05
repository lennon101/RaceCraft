# Authentication Troubleshooting Guide

This guide helps you troubleshoot issues with Supabase authentication in RaceCraft.

## Issue: Sign In Button Not Appearing

If you've configured Supabase environment variables but don't see the "Sign In" button in the header, follow these steps:

### Step 1: Check Railway Environment Variables

In your Railway dashboard:

1. Go to your RaceCraft project
2. Click on **Variables** tab
3. Verify these variables are set:
   - `SUPABASE_URL` - Your Supabase project URL (e.g., `https://xxxxx.supabase.co`)
   - `SUPABASE_ANON_KEY` - Your Supabase anonymous/public key (starts with `eyJ...`)
   - `SUPABASE_SERVICE_KEY` - Your Supabase service role key (starts with `eyJ...`)

**Important**: After adding/changing variables, you must redeploy:
- Railway usually auto-deploys when you push to GitHub
- Or click **Deploy** manually in Railway dashboard

### Step 2: Check Railway Deployment Logs

After deployment, check the logs to see if Supabase initialized:

1. In Railway dashboard, go to **Deployments**
2. Click on the latest deployment
3. View the **Deploy Logs**

Look for one of these messages:

#### ✅ Success - Credentials Loaded
```
✓ Supabase credentials loaded - authentication enabled
  URL: https://your-project.supabase.co
  Anon key: eyJhbGciOiJIUzI1NiI...
```

This means the backend has your credentials and authentication should work.

#### ❌ Not Configured
```
⚠ Warning: Supabase credentials not found in environment variables
  App will run in legacy file-based mode
  Set SUPABASE_URL and SUPABASE_ANON_KEY to enable authentication
```

This means the environment variables are not set or not being read. Go back to Step 1.

#### ⚠️ Import Error
```
⚠ Warning: Failed to import Supabase client library: [error message]
  App will run in legacy file-based mode
```

This means the Supabase Python library isn't installed. This shouldn't happen with the standard deployment, but if it does, check `requirements.txt` includes `supabase==2.3.4`.

### Step 3: Check Browser Console

Open your deployed RaceCraft app and open browser developer tools (F12 or right-click → Inspect).

In the **Console** tab, look for these messages:

#### ✅ Success - Authentication Enabled
```
✓ Supabase authentication initialized
```

This means everything is working! The Sign In button should be visible in the header (top right).

#### ℹ️ Legacy Mode
```
ℹ Supabase not configured - running in legacy mode
```

This means the frontend didn't receive Supabase credentials from the backend. Check:
1. Railway backend logs (Step 2)
2. Network tab - look at response from `/api/auth/check`

#### ❌ Library Not Loaded
```
❌ Supabase library not loaded from CDN
ℹ Running in legacy mode - Supabase authentication disabled
```

This means the Supabase JavaScript library from CDN didn't load. This could be:
- CDN is blocked by your network/browser
- CDN is down (rare)
- Browser extension blocking the script

**Fix**: Try a different browser or network, or check browser extensions.

### Step 4: Test the Auth Check Endpoint

Open your browser's developer tools and run this in the Console:

```javascript
fetch('/api/auth/check').then(r => r.json()).then(console.log)
```

You should see:

#### ✅ Authentication Enabled
```json
{
  "supabase_enabled": true,
  "supabase_url": "https://your-project.supabase.co",
  "supabase_anon_key": "eyJ..."
}
```

The Sign In button should appear.

#### ❌ Authentication Disabled
```json
{
  "supabase_enabled": false,
  "supabase_url": null,
  "supabase_anon_key": null
}
```

No Sign In button will appear. Go back to Step 1 and 2.

### Step 5: Check Supabase Credentials are Valid

Make sure your Supabase credentials are correct:

1. Go to [supabase.com](https://supabase.com) and sign in
2. Open your project
3. Go to **Settings** → **API**
4. Compare these values with your Railway environment variables:
   - **Project URL** should match `SUPABASE_URL`
   - **anon public** key should match `SUPABASE_ANON_KEY`
   - **service_role** key should match `SUPABASE_SERVICE_KEY`

**Note**: These keys are long strings starting with `eyJ`. Make sure you copied them completely without extra spaces or line breaks.

### Step 6: Verify Database Migration

If everything above looks good but authentication still doesn't work when you try to sign up/in:

1. Go to your Supabase project dashboard
2. Go to **SQL Editor**
3. Run the migration from `supabase/migrations/001_create_user_plans.sql`
4. Verify the `user_plans` table exists in **Table Editor**

## Common Issues and Solutions

### Issue: "Sign In button appears but clicking does nothing"

**Check**: Browser console for errors  
**Fix**: The auth modal might not be rendering. Check if `auth-modal` element exists in the page HTML.

### Issue: "Sign In works but plans don't save"

**Check**: Railway logs when saving a plan  
**Fix**: This means the database migration hasn't been run. See Step 6 above.

### Issue: "App works locally but not on Railway"

**Check**: Environment variables are set in Railway, not just in your local `.env` file  
**Fix**: Railway environment variables are separate from your local `.env`. Set them in the Railway dashboard.

### Issue: "After redeploying, authentication stopped working"

**Check**: Environment variables persisted after redeploy  
**Fix**: Environment variables should persist, but verify them in Railway dashboard. Sometimes variables can be accidentally deleted.

## Still Having Issues?

If none of the above helps, gather this information:

1. **Railway Deployment Logs**: Copy the startup messages about Supabase
2. **Browser Console**: Copy any error messages
3. **Auth Check Response**: Result from Step 4
4. **Environment Variables**: Confirm they're set (don't paste actual keys, just confirm they exist)

Then create an issue on GitHub with this information.

## Testing Checklist

After fixing issues, test this flow:

- [ ] Open the app URL
- [ ] See "Sign In" button in top right of header
- [ ] Click "Sign In" - modal should open
- [ ] Try signing up with an email and password
- [ ] After sign up, see your email in header instead of "Sign In" button
- [ ] Create and save a race plan
- [ ] Refresh the page - you should still be logged in
- [ ] Load your saved plan - it should appear in the list
- [ ] Click "Sign Out" - button should change back to "Sign In"

If all these work, authentication is properly configured! 🎉
