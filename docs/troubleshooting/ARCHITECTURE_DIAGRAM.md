# Supabase Integration - Before and After

## Before (Broken)

```
┌─────────────────────────────────────────────────────────────────┐
│ Frontend (Browser)                                               │
│                                                                  │
│  User signs in with Supabase                                    │
│  ↓                                                              │
│  JWT token stored in browser                                    │
│  ↓                                                              │
│  User clicks "Save Plan"                                        │
│  ↓                                                              │
│  authManager.getAuthHeaders()                                   │
│  ↓                                                              │
│  Sends: Authorization: Bearer <jwt_token>                       │
└─────────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ Backend (Flask)                                                  │
│                                                                  │
│  Receives Authorization header ✓                                │
│  ↓                                                              │
│  get_user_from_token() validates JWT ✓                          │
│  ↓                                                              │
│  Extracts user_id from token ✓                                  │
│  ↓                                                              │
│  ❌ PROBLEM: Uses anon key client                               │
│  ↓                                                              │
│  get_supabase_client().table('user_plans').insert({            │
│    owner_id: user_id,                                           │
│    plan_data: {...}                                             │
│  })                                                             │
└─────────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ Supabase Database                                                │
│                                                                  │
│  RLS Policy: "Users can insert own plans"                       │
│  FOR INSERT                                                     │
│  WITH CHECK (auth.uid() = owner_id)                             │
│  ↓                                                              │
│  ❌ FAILS: auth.uid() is NULL                                   │
│     (anon client doesn't set auth context from backend)         │
│  ↓                                                              │
│  ❌ Insert is blocked by RLS policy                             │
│  ↓                                                              │
│  Result: Plan NOT saved to database                             │
└─────────────────────────────────────────────────────────────────┘
```

## After (Fixed)

```
┌─────────────────────────────────────────────────────────────────┐
│ Frontend (Browser)                                               │
│                                                                  │
│  User signs in with Supabase                                    │
│  ↓                                                              │
│  JWT token stored in browser                                    │
│  ↓                                                              │
│  User clicks "Save Plan"                                        │
│  ↓                                                              │
│  authManager.getAuthHeaders()                                   │
│  ↓                                                              │
│  Sends: Authorization: Bearer <jwt_token>                       │
└─────────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ Backend (Flask)                                                  │
│                                                                  │
│  Receives Authorization header ✓                                │
│  ↓                                                              │
│  get_user_from_token() validates JWT ✓                          │
│  ↓                                                              │
│  Extracts user_id from token ✓                                  │
│  ↓                                                              │
│  ✅ FIX: Uses admin client for authenticated users              │
│  ↓                                                              │
│  client = get_supabase_admin_client()  # Service role key       │
│  ↓                                                              │
│  client.table('user_plans').insert({                            │
│    owner_id: user_id,  # Already validated!                     │
│    plan_data: {...}                                             │
│  })                                                             │
└─────────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ Supabase Database                                                │
│                                                                  │
│  ✅ Service role key BYPASSES RLS policies                      │
│  ↓                                                              │
│  Backend has already validated user_id from JWT                 │
│  ↓                                                              │
│  Query explicitly filters by owner_id = user_id                 │
│  ↓                                                              │
│  ✅ Insert succeeds                                             │
│  ↓                                                              │
│  Result: Plan SAVED to database ✓                               │
│                                                                  │
│  Database row:                                                   │
│  - id: <uuid>                                                   │
│  - owner_id: <user_id>  ✓                                       │
│  - anonymous_id: NULL                                           │
│  - plan_name: "My Race Plan"                                    │
│  - plan_data: {...}                                             │
│  - created_at: 2026-02-02 01:00:00                              │
│  - updated_at: 2026-02-02 01:00:00                              │
└─────────────────────────────────────────────────────────────────┘
```

## Anonymous Users (Still Works)

```
┌─────────────────────────────────────────────────────────────────┐
│ Frontend (Browser)                                               │
│                                                                  │
│  User NOT signed in (anonymous)                                 │
│  ↓                                                              │
│  Anonymous ID generated (anon_12345...)                         │
│  ↓                                                              │
│  User clicks "Save Plan"                                        │
│  ↓                                                              │
│  authManager.getAuthHeaders()                                   │
│  ↓                                                              │
│  Sends: X-Anonymous-ID: anon_12345...                           │
└─────────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ Backend (Flask)                                                  │
│                                                                  │
│  Receives X-Anonymous-ID header ✓                               │
│  ↓                                                              │
│  get_user_id_from_request()                                     │
│  ↓                                                              │
│  Returns: {type: 'anonymous', id: 'anon_12345...'}             │
│  ↓                                                              │
│  ✅ Uses anon key client for anonymous users                    │
│  ↓                                                              │
│  client = get_supabase_client()  # Anon key                     │
│  ↓                                                              │
│  client.table('user_plans').insert({                            │
│    anonymous_id: 'anon_12345...',                               │
│    plan_data: {...}                                             │
│  })                                                             │
└─────────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ Supabase Database                                                │
│                                                                  │
│  RLS Policy: "Anonymous users can insert plans"                 │
│  FOR INSERT                                                     │
│  WITH CHECK (auth.uid() IS NULL AND anonymous_id IS NOT NULL)   │
│  ↓                                                              │
│  ✅ PASSES: auth.uid() is NULL, anonymous_id is set             │
│  ↓                                                              │
│  ✅ Insert succeeds                                             │
│  ↓                                                              │
│  Result: Plan SAVED to database ✓                               │
│                                                                  │
│  Database row:                                                   │
│  - id: <uuid>                                                   │
│  - owner_id: NULL                                               │
│  - anonymous_id: "anon_12345..."  ✓                             │
│  - plan_name: "My Race Plan"                                    │
│  - plan_data: {...}                                             │
└─────────────────────────────────────────────────────────────────┘
```

## Key Insight

**The problem:** The anon key client doesn't automatically pass the authenticated user's context to Supabase when called from the backend, even if we validated the JWT token.

**The solution:** Use the service role key (admin client) for authenticated users. Since we've already validated the JWT token on the backend, we can safely bypass RLS and perform operations directly. All queries are still explicitly scoped to the user's ID for security.

**Why it's safe:**
1. Backend validates JWT token first
2. User ID extracted from trusted source (Supabase's JWT)
3. All queries explicitly filter by user ID
4. Service role key never exposed to frontend
5. Alternative would be duplicating RLS logic in code (worse)

## Code Comparison

### Before (Broken)
```python
# Always uses anon client, regardless of user type
query = get_supabase_client().table('user_plans').insert({
    'owner_id': user_id,  # From validated JWT
    'plan_data': data
})
# ❌ Fails due to RLS: auth.uid() not set
```

### After (Fixed)
```python
# Select appropriate client based on user type
client = get_supabase_admin_client() if user_info['type'] == 'authenticated' else get_supabase_client()

# Use selected client
query = client.table('user_plans').insert({
    'owner_id': user_id,  # From validated JWT
    'plan_data': data
})
# ✅ Success: Admin client bypasses RLS
```
