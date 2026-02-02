# Supabase Save/Load Plan Fix

## Problem

When users signed in with Supabase and tried to save or load plans using the UI buttons, the plans were not appearing in the Supabase `user_plans` database table. This happened even though the authentication was working correctly.

## Root Cause

The issue was in how the backend communicated with Supabase for authenticated users:

1. **Frontend correctly sends JWT token**: The frontend's `authManager.getAuthHeaders()` properly sends the user's JWT token in the `Authorization: Bearer <token>` header.

2. **Backend validates the token**: The backend correctly validates the JWT token and extracts the user ID.

3. **Backend uses wrong Supabase client**: However, when performing database operations, the backend was using the **anon key client** (`supabase_client`) instead of the **service role key client** (`supabase_admin_client`).

4. **RLS policies block access**: The Supabase Row Level Security (RLS) policies require `auth.uid()` to be set for authenticated users. When using the anon key client from the backend, this context is not automatically set, causing all database operations to fail silently.

### Why This Matters

Supabase's Row Level Security (RLS) works differently depending on which API key is used:

- **Anon Key Client**: Respects RLS policies. Requires `auth.uid()` to be set in the user's session context. This is automatic in the frontend when users are logged in, but not automatic on the backend.

- **Service Role Key Client**: Bypasses RLS policies entirely. Since the backend has already validated the user's JWT token and extracted their user ID, we can safely use this client to perform operations on their behalf.

## Solution

Updated the backend to use the appropriate Supabase client based on user type:

- **Authenticated users** → Use `get_supabase_admin_client()` (service role key)
  - We've already validated their JWT token
  - We know their user ID
  - Safe to bypass RLS and perform operations directly

- **Anonymous users** → Use `get_supabase_client()` (anon key)
  - They provide an anonymous session ID
  - RLS policies allow access based on `anonymous_id` column
  - This works correctly with the anon key client

## Files Changed

### `app.py`

Updated the following endpoints to use the correct Supabase client:

1. **`/api/save-plan`** (Line ~1057-1095)
   - Added logic to select appropriate client based on user type
   - Uses admin client for authenticated users
   - Uses regular client for anonymous users

2. **`/api/list-plans`** (Line ~1118-1150)
   - Same client selection logic
   - Queries user's plans with correct authorization

3. **`/api/load-plan/<filename>`** (Line ~1175-1207)
   - Uses appropriate client for loading plan data
   - Maintains fallback to file-based storage

4. **`/api/delete-plan/<filename>`** (Line ~1227-1270)
   - Correctly authorizes plan deletion based on user type

5. **`/api/auth/list-anonymous-plans`** (Line ~1436-1465)
   - Uses admin client for listing anonymous plans
   - Bypasses RLS since we're doing admin operations for migration

## Code Pattern

The fix follows this pattern in each affected endpoint:

```python
# Determine user type and ID
owner_id = user_info['id'] if user_info['type'] == 'authenticated' else None
anonymous_id = user_info['id'] if user_info['type'] == 'anonymous' else None

# Use admin client for authenticated users (bypasses RLS since we've already validated)
# Use regular client for anonymous users (RLS allows anonymous_id based access)
client = get_supabase_admin_client() if owner_id else get_supabase_client()
if not client:
    raise Exception("Supabase client not available")

# Perform database operation with the correct client
query = client.table('user_plans').select('...')
# ... rest of the query
```

## Testing Checklist

To verify the fix works correctly:

### Authenticated User Flow
- [x] Sign in with Supabase account
- [ ] Save a new race plan
- [ ] Verify plan appears in Supabase `user_plans` table with `owner_id` set
- [ ] Load the saved plan
- [ ] Save another plan with a different name
- [ ] List all plans (should show both)
- [ ] Update existing plan (save with same name)
- [ ] Delete a plan
- [ ] Sign out and sign back in
- [ ] Verify plans persist across sessions

### Anonymous User Flow
- [ ] Use app without signing in
- [ ] Save a race plan
- [ ] Verify plan appears in Supabase `user_plans` table with `anonymous_id` set
- [ ] Load the plan
- [ ] List plans
- [ ] Delete the plan

### Migration Flow
- [ ] Create plans as anonymous user
- [ ] Sign up for an account
- [ ] Verify migration modal appears
- [ ] Import plans
- [ ] Verify plans now have `owner_id` instead of `anonymous_id`

## Security Considerations

This fix is secure because:

1. **Authentication is validated first**: The backend validates the JWT token before performing any operations.

2. **User ID is extracted from trusted source**: The user ID comes from Supabase's own JWT validation, not from user input.

3. **Service role key never exposed**: The service role key remains on the backend only and is never sent to the frontend.

4. **Operations scoped to authenticated user**: All database queries explicitly filter by `owner_id = user_info['id']`, ensuring users can only access their own data.

5. **Anonymous users still protected**: Anonymous users continue to use the anon key client with RLS policies enforced.

## Alternative Approaches Considered

### Option 1: Set auth context on anon key client
We could try to set the auth context on the anon key client using the user's JWT token. However:
- This is more complex to implement
- May not work reliably across all Supabase operations
- Requires passing tokens through the client in a non-standard way

### Option 2: Use Supabase Auth API directly
We could bypass the RLS policies by using Supabase's Auth API directly. However:
- This duplicates RLS policy logic in application code
- More error-prone and harder to maintain
- The service role approach is cleaner and more idiomatic

### Option 3: Frontend-only operations (Chosen approach + this)
The frontend could perform database operations directly using the user's JWT token. However:
- We want to keep some backend validation
- Need backend for file-based fallback mode
- Current architecture already validates on backend

The chosen approach (using service role key on backend after validation) is the cleanest and most maintainable solution.

## Related Documentation

- See `AUTHENTICATION.md` for authentication system overview
- See `supabase/migrations/001_create_user_plans.sql` for RLS policies
- See `supabase/SETUP.md` for Supabase configuration guide
