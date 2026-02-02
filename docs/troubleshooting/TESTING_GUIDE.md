# Testing Guide for Supabase Save/Load Plan Fix

This guide will help you verify that the Supabase integration fix is working correctly.

## Prerequisites

1. Supabase project must be configured with:
   - `SUPABASE_URL` environment variable
   - `SUPABASE_ANON_KEY` environment variable
   - `SUPABASE_SERVICE_KEY` environment variable
   
2. Database migration must be applied:
   - Run the SQL in `supabase/migrations/001_create_user_plans.sql`
   - Verify `user_plans` table exists in Supabase dashboard

3. Application must be running:
   ```bash
   python app.py
   # or
   docker-compose up
   ```

## Test 1: Authenticated User - Save Plan

**Steps:**
1. Open the RaceCraft application in your browser
2. Click "Sign In" button (or create an account if you don't have one)
3. Sign in with your Supabase credentials
4. Upload a GPX file or use existing route data
5. Fill in race planning parameters (pacing, nutrition, etc.)
6. Click "Calculate" to generate a race plan
7. Click "Save Plan" button
8. Enter a plan name (e.g., "Test Plan 1")
9. Click "Save"

**Expected Results:**
- ✅ Alert shows "Plan saved successfully!"
- ✅ In Supabase dashboard → Table Editor → user_plans:
  - New row appears with `plan_name` = "Test Plan 1"
  - `owner_id` is set to your user ID (UUID format)
  - `anonymous_id` is NULL
  - `plan_data` contains your race plan details (JSON)
  - `created_at` and `updated_at` timestamps are set

**What to check in Supabase:**
```sql
-- Run this query in Supabase SQL Editor to verify
SELECT id, owner_id, anonymous_id, plan_name, created_at, updated_at
FROM user_plans
WHERE owner_id IS NOT NULL
ORDER BY created_at DESC;
```

## Test 2: Authenticated User - List Plans

**Steps:**
1. While still signed in from Test 1
2. Click "Load Plan" button
3. Modal should open showing list of saved plans

**Expected Results:**
- ✅ Modal opens successfully
- ✅ "Test Plan 1" appears in the list
- ✅ Shows the correct modification timestamp
- ✅ No error messages in browser console

**Browser Console Check:**
1. Press F12 to open Developer Tools
2. Check Console tab for errors
3. Should see: "✓ Supabase authentication initialized"
4. Should NOT see: "Supabase list error" or similar errors

## Test 3: Authenticated User - Load Plan

**Steps:**
1. With Load Plan modal still open
2. Click on "Test Plan 1" to load it

**Expected Results:**
- ✅ Modal closes
- ✅ Plan loads successfully
- ✅ All fields populate with saved values:
  - GPX filename
  - Checkpoint distances
  - Pacing parameters (Z2 pace, climbing ability)
  - Nutrition settings (carbs/hour, water/hour)
  - Fatigue settings
  - Skill level
- ✅ Race plan calculations appear in results area
- ✅ Alert shows "Plan loaded successfully!" (if implemented)

## Test 4: Authenticated User - Update Plan

**Steps:**
1. After loading a plan from Test 3
2. Make a small change (e.g., modify carbs per hour)
3. Click "Calculate" to recalculate
4. Click "Save Plan" button
5. Keep the same plan name ("Test Plan 1")
6. Click "Save"

**Expected Results:**
- ✅ Alert shows "Plan updated successfully!"
- ✅ In Supabase dashboard:
  - Same plan row (same ID)
  - `updated_at` timestamp is more recent
  - `plan_data` reflects the changes

## Test 5: Authenticated User - Delete Plan

**Steps:**
1. Click "Load Plan" button
2. Find "Test Plan 1" in the list
3. Click the "Delete" button next to it
4. Confirm deletion if prompted

**Expected Results:**
- ✅ Plan disappears from the list immediately
- ✅ In Supabase dashboard:
  - Row is deleted from user_plans table
- ✅ Alert shows "Plan deleted successfully!"

## Test 6: Authenticated User - Multiple Plans

**Steps:**
1. Create and save 3 different plans:
   - "Marathon Plan"
   - "50K Ultra"
   - "100 Mile Race"
2. Click "Load Plan" to view the list

**Expected Results:**
- ✅ All three plans appear in the list
- ✅ Plans are sorted by modification time (newest first)
- ✅ Each plan has correct name and timestamp
- ✅ Can load any plan by clicking it
- ✅ In Supabase dashboard:
  - Three rows exist with your owner_id
  - Each has unique plan_name

## Test 7: Authenticated User - Persistence

**Steps:**
1. Sign out of the application
2. Close browser tab
3. Open a new browser tab
4. Navigate to RaceCraft
5. Sign in with same credentials
6. Click "Load Plan"

**Expected Results:**
- ✅ All previously saved plans still appear
- ✅ Plans persist across sessions
- ✅ Can load and edit any saved plan

## Test 8: Anonymous User - Basic Save/Load

**Steps:**
1. Sign out (or use incognito/private browsing mode)
2. Navigate to RaceCraft
3. Upload a GPX file and create a race plan
4. Click "Save Plan"
5. Enter a plan name "Anonymous Test Plan"
6. Click "Save"
7. Click "Load Plan"

**Expected Results:**
- ✅ Plan saves successfully
- ✅ Plan appears in the load list
- ✅ In Supabase dashboard:
  - New row with `anonymous_id` set (format: "anon_xxxxx")
  - `owner_id` is NULL
  - `plan_data` contains the plan

**Check anonymous ID:**
1. Press F12 → Application (Chrome) or Storage (Firefox)
2. Local Storage → your domain
3. Find `racecraft_anonymous_id`
4. This value should match `anonymous_id` in database

## Test 9: Migration from Anonymous to Authenticated

**Steps:**
1. As anonymous user (from Test 8)
2. Create 2-3 plans
3. Click "Sign Up" and create a new account
4. Complete sign up process

**Expected Results:**
- ✅ Migration modal appears showing your anonymous plans
- ✅ Plans are checked by default
- ✅ Can select/deselect individual plans
- ✅ Click "Import Selected"
- ✅ Success message shows number of plans imported
- ✅ In Supabase dashboard:
  - Plans now have `owner_id` (your new user ID)
  - `anonymous_id` is NULL
  - Plan data unchanged

## Test 10: Cross-Device Sync (Authenticated)

**Steps:**
1. On Device A: Sign in and save a plan "Device A Plan"
2. On Device B: Sign in with same account
3. Click "Load Plan"

**Expected Results:**
- ✅ "Device A Plan" appears in the list on Device B
- ✅ Can load and edit the plan on Device B
- ✅ Changes sync via Supabase

## Common Issues and Troubleshooting

### Issue: "Plan saved successfully" but not in Supabase

**Possible Causes:**
1. Service role key not set → Check `SUPABASE_SERVICE_KEY` environment variable
2. Wrong Supabase project → Verify `SUPABASE_URL` matches your project
3. RLS policies not applied → Run migration script in Supabase SQL Editor

**Debug Steps:**
1. Check backend logs for "Supabase save error"
2. Verify all three environment variables are set
3. Check Supabase dashboard logs (Logs & Reports)

### Issue: Plans don't load after sign in

**Possible Causes:**
1. JWT token not being sent → Check browser Network tab
2. User ID mismatch → Check token validation
3. RLS policies blocking access → Verify migration was applied

**Debug Steps:**
1. Open browser DevTools → Network tab
2. Click "Load Plan" and check the request
3. Verify `Authorization: Bearer <token>` header is present
4. Check response for errors

### Issue: Anonymous plans don't save

**Possible Causes:**
1. Anonymous ID not generated → Check localStorage
2. RLS policies too restrictive → Verify policies allow anonymous_id

**Debug Steps:**
1. Press F12 → Console
2. Type: `localStorage.getItem('racecraft_anonymous_id')`
3. Should return a value like "anon_1234567890_abc123"
4. If null, the anonymous ID generation failed

## Verification Checklist

Before considering the fix complete, verify:

- [ ] Authenticated users can save plans (Test 1)
- [ ] Authenticated users can list plans (Test 2)
- [ ] Authenticated users can load plans (Test 3)
- [ ] Authenticated users can update plans (Test 4)
- [ ] Authenticated users can delete plans (Test 5)
- [ ] Plans persist across sessions (Test 7)
- [ ] Anonymous users can save/load plans (Test 8)
- [ ] Migration works correctly (Test 9)
- [ ] No security vulnerabilities (run CodeQL)
- [ ] No errors in browser console
- [ ] No errors in backend logs

## Success Criteria

The fix is successful when:

1. ✅ Authenticated users can save plans to Supabase user_plans table
2. ✅ Plans appear with correct `owner_id` in database
3. ✅ Plans persist across browser sessions and devices
4. ✅ Anonymous users can still save/load plans locally
5. ✅ Migration from anonymous to authenticated works
6. ✅ No security vulnerabilities introduced
7. ✅ No errors in console or logs during normal operations

## SQL Queries for Manual Verification

Run these in Supabase SQL Editor to verify data:

```sql
-- Check all plans for authenticated users
SELECT 
    id,
    owner_id,
    plan_name,
    created_at,
    updated_at,
    plan_data->>'plan_name' as display_name
FROM user_plans
WHERE owner_id IS NOT NULL
ORDER BY updated_at DESC;

-- Check all plans for anonymous users
SELECT 
    id,
    anonymous_id,
    plan_name,
    created_at,
    updated_at,
    plan_data->>'plan_name' as display_name
FROM user_plans
WHERE anonymous_id IS NOT NULL
ORDER BY updated_at DESC;

-- Check plans for specific user
SELECT 
    id,
    plan_name,
    created_at,
    updated_at
FROM user_plans
WHERE owner_id = 'YOUR_USER_ID_HERE'
ORDER BY updated_at DESC;

-- Verify constraint (should return 0 rows)
SELECT *
FROM user_plans
WHERE owner_id IS NOT NULL AND anonymous_id IS NOT NULL;
```

## Additional Notes

- The fix uses the service role key (admin client) for authenticated users
- This is secure because JWT tokens are validated before operations
- Anonymous users continue to use the anon key (regular client)
- RLS policies still protect data at the database level
- All operations are scoped to the authenticated user's ID

For more technical details, see `SUPABASE_FIX.md`.
