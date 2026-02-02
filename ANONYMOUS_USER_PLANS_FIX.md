# Anonymous User Plans Fix - Implementation Summary

## Problem
Anonymous users could save plans to Supabase, but couldn't see them in the Load Plans feature.

## Before Fix

```
User saves plan without login
    ↓
Save to Supabase with anonymous_id ✓
    ↓
User clicks "Load Plans"
    ↓
list_plans() checks: user_info['type'] == 'authenticated' ✗
    ↓
Anonymous plans NOT displayed ✗
```

## After Fix

```
User saves plan without login
    ↓
Save to Supabase with anonymous_id ✓
    ↓
User clicks "Load Plans"
    ↓
list_plans() checks: user_info exists? ✓
    ↓
Query Supabase by anonymous_id ✓
    ↓
Anonymous plans DISPLAYED with "Account" badge ✓
```

## Technical Changes

### 1. `/api/list-plans` endpoint
**Changed:** Line 1252
```python
# BEFORE
if user_info and user_info['type'] == 'authenticated':

# AFTER  
if user_info:  # Accept both authenticated and anonymous
```

**Added:** Client selection logic
```python
# Use appropriate client based on user type
client = (get_supabase_admin_client() if user_info['type'] == 'authenticated' 
          else get_supabase_client())
```

**Added:** Query filtering logic
```python
if user_info['type'] == 'authenticated':
    query = query.eq('owner_id', user_info['id'])
else:  # anonymous
    query = query.eq('anonymous_id', user_info['id'])
```

### 2. `/api/load-plan` endpoint
Similar changes to support loading anonymous user plans from Supabase.

### 3. `/api/delete-plan` endpoint
Similar changes to support deleting anonymous user plans from Supabase.

## Plan Display Behavior

| User Type      | Local Plans | Supabase Plans | Badge Color |
|----------------|-------------|----------------|-------------|
| Not logged in  | ✓ Shown     | ✓ Shown (if anonymous_id) | Blue/Green |
| Anonymous user | ✓ Shown     | ✓ Shown       | Blue/Green  |
| Authenticated  | ✓ Shown     | ✓ Shown       | Blue/Green  |

- **Blue badge** = "Local" (saved to disk)
- **Green badge** = "Account" (saved to Supabase)

## Security Model

### Authenticated Users
- Use `get_supabase_admin_client()` to bypass RLS
- Query by `owner_id`
- Full access to their own plans

### Anonymous Users
- Use `get_supabase_client()` with RLS enforced
- Query by `anonymous_id`
- Access controlled by Supabase RLS policies

## Testing Results

✅ All API endpoints accept anonymous users
✅ No 401 errors for anonymous users
✅ Backward compatible with local plans
✅ Consistent behavior across list/load/delete operations

## Impact

🎉 **Anonymous users can now:**
- See their Supabase-saved plans in Load Plans modal
- Load their previously saved plans
- Delete their plans
- Continue using the app without signing up

This maintains a smooth user experience while still encouraging migration to authenticated accounts.
