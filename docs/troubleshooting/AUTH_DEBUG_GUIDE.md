# AUTH DEBUG: Authorization Header Not Being Sent

## Current Status

Your logs show:
```
User info from request: None
⚠️  No user_info - falling back to file-based storage
```

This means the backend isn't getting authentication information from the frontend.

## What I've Added

I've added **extremely detailed logging** to the authentication flow that will show:

1. Whether the Authorization header is being sent
2. The first 50 characters of the header (to verify format)
3. Whether token validation is attempted
4. Whether token validation succeeds or fails
5. The exact error if validation fails
6. Whether anonymous ID is being used as fallback

## What to Do Next

### Step 1: Redeploy on Railway

The enhanced logging is in the repository. Redeploy to get the new logs.

### Step 2: Try Saving a Plan

1. Make sure you're **signed in** (check top-right corner of RaceCraft UI)
2. Create or load a race plan
3. Click "Save Plan"
4. Enter a plan name and save

### Step 3: Check Railway Logs

Look for logs starting with `🔐 get_user_id_from_request called`

## Expected Scenarios

### Scenario 1: Authorization Header NOT Being Sent (Most Likely)

```
🚀 SAVE PLAN REQUEST START - Plan name: 'test'
   Supabase enabled: True
   User info from request: None
🔐 get_user_id_from_request called
   Authorization header present: False
   Authorization header value: None...
   ⚠️ No Authorization header in request
   X-Anonymous-ID header: anon_1234567890_abcdef
   Using anonymous ID: anon_1234567890_abcdef
⚠️  No user_info - falling back to file-based storage
```

**What this means**: 
- Frontend isn't sending the Authorization header
- Most likely: `currentUser` is not set in the frontend
- Or: Session doesn't have access_token

**Why this happens**:
- User might not be fully logged in on frontend
- Session might have expired
- Frontend Supabase client not initialized properly

**How to verify on frontend**:
1. Open browser DevTools → Console
2. Look for: "✓ Supabase authentication initialized"
3. Type in console: `authManager.currentUser`
   - Should show user object if logged in
   - Shows null if not logged in
4. Type: `await authManager.supabase.auth.getSession()`
   - Should show session with access_token

### Scenario 2: Header Sent But Token Validation Fails

```
🔐 get_user_id_from_request called
   Authorization header present: True
   Authorization header value: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   Attempting to validate token...
   Validating token (length: 250)
   ❌ Error validating token: Invalid token
   ❌ Token validation failed or returned no user
```

**What this means**:
- Frontend IS sending the header
- But backend can't validate the token
- Could be expired token, wrong key, or network issue

**Possible causes**:
- Token expired
- SUPABASE_ANON_KEY mismatch between frontend/backend
- Supabase project settings issue

### Scenario 3: Validation Succeeds But User Object Wrong

```
🔐 get_user_id_from_request called
   Authorization header present: True
   Attempting to validate token...
   Token validation successful: True
   User object has .user attribute: False
   ❌ Token validation failed or returned no user
```

**What this means**:
- Token validation returns something
- But the response structure is unexpected
- Might be API version mismatch

### Scenario 4: Everything Works! (What We Want)

```
🔐 get_user_id_from_request called
   Authorization header present: True
   Authorization header value: Bearer eyJhbGciOiJIUzI1NiIs...
   Attempting to validate token...
   Validating token (length: 250)
   Token validation successful: True
   User object has .user attribute: True
   user.user value: User(id='12345678-1234-1234-1234-123456789012'...)
   ✓ Authenticated user found: 12345678-1234-1234-1234-123456789012
📝 Save plan request - User type: authenticated, ID: 12345678...
✓ Inserted new plan...
```

**Result**: Plan saved to Supabase! ✓

## Quick Debugging Steps

### Check 1: Are You Actually Signed In?

Look at the top-right corner of RaceCraft UI:
- Should show your email or user name
- Should have "Sign Out" button
- If you see "Sign In", you're NOT signed in!

### Check 2: Check Browser Console

Open DevTools → Console and run:
```javascript
// Check if auth manager exists
console.log('Auth Manager:', authManager);

// Check current user
console.log('Current User:', authManager?.currentUser);

// Check session
authManager?.supabase?.auth.getSession().then(session => {
    console.log('Session:', session);
    console.log('Has access token:', !!session?.data?.session?.access_token);
});
```

### Check 3: Check Network Tab

In DevTools → Network tab:
1. Filter for "save-plan"
2. Click on the request
3. Go to "Headers" section
4. Look for "Authorization" in Request Headers
   - Should show: `Bearer eyJhbGciOiJIUzI1NiIs...`
   - If missing: Frontend isn't sending it

## Most Likely Issue

Based on your logs showing "User info from request: None", the most likely issue is:

**Scenario 1**: Authorization header not being sent because:
- Frontend `currentUser` is null even though you signed in
- OR session doesn't have access_token
- OR frontend Supabase client not initialized

## What to Report Back

After redeploying and trying to save, please share:

1. **Railway logs** starting with `🔐 get_user_id_from_request called`
2. **Browser console output** of:
   ```javascript
   console.log(authManager.currentUser);
   console.log(await authManager.supabase.auth.getSession());
   ```
3. **Network tab** - Is Authorization header in the save-plan request?
4. **UI status** - Does top-right corner show you're signed in?

This will tell us exactly where the auth flow is breaking!

## Next Steps Based on Scenario

**If Scenario 1** (no header):
→ Fix frontend to ensure currentUser is set after login

**If Scenario 2** (validation fails):
→ Check token expiration, verify SUPABASE_ANON_KEY matches

**If Scenario 3** (wrong user object):
→ Update backend to handle different response structure

**If Scenario 4** (works!):
→ Celebrate! Plans will save to Supabase! 🎉
