# Debugging: Plans Show Success But Don't Save

## Problem
The app shows "Plan updated successfully!" but no rows appear in the Supabase `user_plans` table.

## What Changed

The save_plan endpoint now **verifies the database operation actually succeeded** before returning success.

### Before (The Bug)
```python
result = client.table('user_plans').insert(plan_record).execute()
print(f"✓ Inserted new plan...")
return jsonify({'message': 'Plan saved successfully'})  # Always returns success!
```

**Problem**: The code assumed success after `execute()` completed without exception, but:
- The operation might fail silently (e.g., RLS policy violation)
- `result.data` might be empty
- `result.error` might contain an error message

### After (The Fix)
```python
result = client.table('user_plans').insert(plan_record).execute()

# Verify the insert succeeded
if hasattr(result, 'error') and result.error:
    return jsonify({'error': f'Failed to insert plan: {result.error}'}), 500

if not result.data:
    return jsonify({'error': 'Insert returned no data - check RLS policies'}), 500

print(f"✓ Inserted new plan...")
return jsonify({'message': 'Plan saved successfully'})
```

**Now**: The code checks if the operation actually succeeded before returning success.

## What to Expect Now

### If Save Succeeds
- ✅ You'll see: "Plan saved successfully!"
- ✅ Backend logs show: `✓ Inserted new plan 'YourPlan' for user [user-id]`
- ✅ Backend logs show: `Result data: [{'id': '...', ...}]`
- ✅ Plan appears in Supabase `user_plans` table

### If Save Fails
- ❌ You'll see an **error message** explaining why
- 📋 Possible error messages:
  - "Failed to insert plan: [error details]"
  - "Insert returned no data - check RLS policies"
  - "Supabase admin client not available"

### Enhanced Logging

The backend now logs detailed information:
```
📝 Save plan request - User type: authenticated, ID: abc-123-def
  Plan name: 'My Marathon Plan'
  Owner ID: abc-123-def
  Anonymous ID: None
✓ Inserted new plan 'My Marathon Plan' for user abc-123-def
  Result data: [{'id': '456', 'owner_id': 'abc-123-def', ...}]
```

Or if it fails:
```
📝 Save plan request - User type: authenticated, ID: abc-123-def
  Plan name: 'My Marathon Plan'
  Owner ID: abc-123-def
  Anonymous ID: None
❌ Insert returned no data - operation may have failed. Check RLS policies.
  Attempted insert with owner_id=abc-123-def, anonymous_id=None
```

## How to Test

### Step 1: Redeploy
The fix is in the repository. Redeploy your application to Railway.

### Step 2: Try Saving a Plan
1. Sign in to RaceCraft
2. Create or load a race plan
3. Click "Save Plan"
4. Enter a plan name and save

### Step 3: Check the Result

**If you see "Plan saved successfully!":**
- ✅ Check Supabase Dashboard → user_plans table
- ✅ Your plan should be there!

**If you see an error message:**
- 📋 Read the error message carefully
- 🔍 Check backend logs for details
- 📊 Follow troubleshooting below

## Troubleshooting

### Error: "Insert returned no data - check RLS policies"

**Cause**: The database operation completed but returned no data. Most common cause: **RLS policy blocking the insert**.

**Check RLS Policies**:
1. Go to Supabase Dashboard → Table Editor → user_plans
2. Click on the table → Policies tab
3. Verify the "Users can insert own plans" policy exists:
   ```sql
   CREATE POLICY "Users can insert own plans" ON public.user_plans
   FOR INSERT
   WITH CHECK (
     (auth.uid() IS NOT NULL AND owner_id = auth.uid() AND anonymous_id IS NULL)
   );
   ```

**The Issue**: When using the admin client (service role key), `auth.uid()` is NULL because we're bypassing authentication. But the RLS policy expects `auth.uid()` to match `owner_id`.

**Solution Options**:

**Option A: Use RLS with admin client** (Recommended)
The admin client should bypass RLS completely, but if RLS is being enforced, we need to adjust the code.

**Option B: Modify RLS policy**
Change the policy to allow service role:
```sql
-- Modify the insert policy to allow service role
CREATE POLICY "Service role can insert plans" ON public.user_plans
FOR INSERT
TO service_role
USING (true)
WITH CHECK (true);
```

**Option C: Verify admin client is actually being used**
Check logs for:
```
📝 Save plan request - User type: authenticated, ID: [your-id]
```

The user type should be "authenticated" for logged-in users.

### Error: "Failed to insert plan: [error details]"

**Cause**: Supabase returned a specific error. The error message will tell you what went wrong.

**Common errors**:
- "duplicate key value" → Plan with this name already exists
- "violates foreign key constraint" → owner_id doesn't exist in auth.users
- "permission denied" → RLS policy issue

**Action**: Read the error message and address the specific issue.

### Error: "Supabase admin client not available"

**Cause**: The admin client (service role key) isn't initialized.

**Fix**: Ensure `SUPABASE_SERVICE_KEY` environment variable is set in Railway.

### No Error But Still No Data

If you see "Plan saved successfully!" but still no data in Supabase:

1. **Check Railway logs**:
   - Look for the save request logs
   - Check if `Result data:` shows actual data
   - Look for any errors after the success message

2. **Verify credentials**:
   - Go to Supabase Dashboard → Settings → API
   - Confirm URL and keys match Railway environment variables
   - Check that the project is the correct one

3. **Check user_id**:
   - The logs show: `Owner ID: [value]`
   - This should match your user ID in Supabase
   - Verify in Supabase Dashboard → Authentication → Users

## Expected Railway Log Output

### Successful Save
```
📝 Save plan request - User type: authenticated, ID: 12345678-1234-1234-1234-123456789012
  Plan name: 'Test Plan'
  Owner ID: 12345678-1234-1234-1234-123456789012
  Anonymous ID: None
✓ Inserted new plan 'Test Plan' for user 12345678-1234-1234-1234-123456789012
  Result data: [{'id': 'abc-def-ghi', 'owner_id': '12345678-1234-1234-1234-123456789012', 'plan_name': 'Test Plan', ...}]
```

### Failed Save (RLS Issue)
```
📝 Save plan request - User type: authenticated, ID: 12345678-1234-1234-1234-123456789012
  Plan name: 'Test Plan'
  Owner ID: 12345678-1234-1234-1234-123456789012
  Anonymous ID: None
❌ Insert returned no data - operation may have failed. Check RLS policies.
  Attempted insert with owner_id=12345678-1234-1234-1234-123456789012, anonymous_id=None
```

## Next Steps

1. **Redeploy** your application on Railway
2. **Try saving** a plan
3. **Check Railway logs** to see the detailed output
4. **Report back** with:
   - The exact error message (if any)
   - The Railway log output for the save attempt
   - Whether you see the result data in logs

This will tell us exactly what's happening and why plans aren't saving!
