# RaceCraft Authentication System

## Overview

RaceCraft implements a flexible authentication system using Supabase that supports both anonymous and authenticated users. The system provides a low-friction entry point while enabling secure data management and multi-device sync for users who choose to create accounts.

## Architecture

### Dual-Mode Operation

RaceCraft operates in two modes:

1. **Legacy Mode (Default)**: No authentication required
   - Activated when Supabase credentials are not provided
   - Plans are stored in the file system or browser localStorage
   - Perfect for single-device usage or testing

2. **Authenticated Mode**: Supabase-powered authentication
   - Activated when `SUPABASE_URL` and `SUPABASE_ANON_KEY` are configured
   - Plans are stored in Supabase database with proper user ownership
   - Supports anonymous sessions and authenticated accounts
   - Enables multi-device sync and secure data isolation

### User Types

#### Anonymous Users
- **Automatic Creation**: An anonymous session ID is generated on first visit
- **Local Storage**: Session ID stored in browser's localStorage
- **Data Association**: Plans are associated with the anonymous ID
- **Persistence**: Data persists across browser sessions
- **No Login Required**: Immediate access to all features

#### Authenticated Users
- **Account Creation**: Email/password or magic link authentication
- **Data Migration**: Anonymous plans are automatically migrated upon signup
- **Multi-Device Access**: Access plans from any device
- **Security**: Row Level Security (RLS) ensures data isolation

## Authentication Flow

### Anonymous User Flow

```
User Visits App
    ↓
Anonymous ID Generated
    ↓
Stored in localStorage
    ↓
User Creates Plans → Associated with Anonymous ID
    ↓
Plans Saved to DB (anonymous_id column)
```

### Account Creation Flow

```
Anonymous User Clicks "Sign Up"
    ↓
Authentication Modal Opens
    ↓
User Enters Email/Password
    ↓
Supabase Creates Account
    ↓
Migration Triggered
    ↓
Anonymous Plans Reassigned to User ID
    ↓
Anonymous ID Cleared
    ↓
User Now Authenticated
```

### Sign In Flow

```
User Clicks "Sign In"
    ↓
Authentication Modal Opens
    ↓
User Enters Credentials (or uses Magic Link)
    ↓
Supabase Validates
    ↓
Session Created
    ↓
User's Plans Loaded
```

## Database Schema

### user_plans Table

```sql
CREATE TABLE user_plans (
    id UUID PRIMARY KEY,
    owner_id UUID REFERENCES auth.users(id),  -- Authenticated user
    anonymous_id TEXT,                         -- Anonymous session
    plan_name TEXT NOT NULL,
    plan_data JSONB NOT NULL,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    
    -- Constraint: Either owner_id OR anonymous_id must be set
    CONSTRAINT check_ownership CHECK (
        (owner_id IS NOT NULL AND anonymous_id IS NULL) OR
        (owner_id IS NULL AND anonymous_id IS NOT NULL)
    )
);
```

### Row Level Security Policies

The database enforces strict data isolation:

- **Authenticated Users**: Can only access rows where `owner_id = auth.uid()`
- **Anonymous Users**: Can only access rows where `anonymous_id` matches their session
- **No Cross-User Access**: Users cannot see or modify other users' data

## API Integration

### Backend (Python/Flask)

#### Authentication Helpers

```python
def get_user_id_from_request():
    """Get user ID from request, supporting both authenticated and anonymous users."""
    auth_header = request.headers.get('Authorization')
    
    if auth_header and supabase_client:
        user = get_user_from_token(auth_header)
        if user:
            return {'type': 'authenticated', 'id': user.user.id}
    
    anonymous_id = request.headers.get('X-Anonymous-ID')
    if anonymous_id:
        return {'type': 'anonymous', 'id': anonymous_id}
    
    return None
```

#### Plan Management with Ownership

All plan endpoints (save, load, list, delete) check user ownership:

```python
@app.route('/api/save-plan', methods=['POST'])
def save_plan():
    user_info = get_user_id_from_request()
    
    if user_info:
        # Supabase mode - use database
        owner_id = user_info['id'] if user_info['type'] == 'authenticated' else None
        anonymous_id = user_info['id'] if user_info['type'] == 'anonymous' else None
        
        # Save to database with ownership
        supabase_client.table('user_plans').insert({
            'owner_id': owner_id,
            'anonymous_id': anonymous_id,
            'plan_name': plan_name,
            'plan_data': save_data
        }).execute()
    else:
        # Legacy mode - use file system
        # ... file-based storage
```

### Frontend (JavaScript)

#### Authentication Manager

```javascript
class AuthManager {
    constructor() {
        this.supabase = null;
        this.currentUser = null;
        this.anonymousId = this.getOrCreateAnonymousId();
    }
    
    async initialize() {
        // Check if Supabase is configured
        const response = await fetch('/api/auth/check');
        const data = await response.json();
        
        if (data.supabase_enabled) {
            this.supabase = createClient(data.supabase_url, data.supabase_anon_key);
            // Set up auth state listener
            this.supabase.auth.onAuthStateChange((event, session) => {
                this.handleAuthStateChange(session);
            });
        }
    }
    
    async getAuthHeaders() {
        const headers = {'Content-Type': 'application/json'};
        
        if (this.currentUser) {
            const session = await this.supabase.auth.getSession();
            headers['Authorization'] = `Bearer ${session.data.session.access_token}`;
        } else if (this.anonymousId) {
            headers['X-Anonymous-ID'] = this.anonymousId;
        }
        
        return headers;
    }
}
```

#### API Calls with Auth

```javascript
async function savePlan(planData) {
    const headers = await authManager.getAuthHeaders();
    
    const response = await fetch('/api/save-plan', {
        method: 'POST',
        headers: headers,
        body: JSON.stringify(planData)
    });
    
    // ... handle response
}
```

## Migration Process

When an anonymous user creates an account, their existing plans are automatically migrated:

### Backend Migration Function

```python
@app.route('/api/auth/migrate', methods=['POST'])
def migrate_anonymous_data():
    user_id = get_authenticated_user_id()
    anonymous_id = request.json.get('anonymous_id')
    
    # Call Supabase function to migrate plans
    result = supabase_admin_client.rpc(
        'migrate_anonymous_plans',
        {'p_anonymous_id': anonymous_id, 'p_user_id': user_id}
    ).execute()
    
    return jsonify({'migrated_plans': result.data})
```

### SQL Migration Function

```sql
CREATE OR REPLACE FUNCTION migrate_anonymous_plans(
    p_anonymous_id TEXT,
    p_user_id UUID
) RETURNS INTEGER AS $$
BEGIN
    UPDATE user_plans
    SET 
        owner_id = p_user_id,
        anonymous_id = NULL,
        updated_at = NOW()
    WHERE anonymous_id = p_anonymous_id;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

## Security Considerations

### Row Level Security (RLS)

RLS is the primary security mechanism:

```sql
-- Users can only view their own plans
CREATE POLICY "Users can view own plans" ON user_plans
    FOR SELECT
    USING (auth.uid() = owner_id);

-- Anonymous users can view plans with their session ID
CREATE POLICY "Anonymous users can view own plans" ON user_plans
    FOR SELECT
    USING (anonymous_id IS NOT NULL);
```

### Key Security Features

1. **No Credential Exposure**: Service role key is never sent to the frontend
2. **Token-Based Auth**: JWT tokens for authenticated users
3. **Anonymous Session IDs**: Unpredictable, stored client-side only
4. **HTTPS Required**: All authentication requires secure connections in production
5. **RLS Enforcement**: Database-level security prevents unauthorized access

## User Experience

### Anonymous User Experience

```
1. User visits RaceCraft
2. Can immediately use all features
3. Plans are saved locally
4. Optional prompt: "Create account to save across devices"
```

### Creating an Account

```
1. User clicks "Sign In" button in header
2. Modal opens with three tabs:
   - Sign In (email/password)
   - Sign Up (email/password)
   - Magic Link (passwordless)
3. User fills in form and submits
4. Success message shows: "X plans migrated to your account"
5. Modal closes automatically
6. User info appears in header with email and logout button
```

### Authenticated User Experience

```
1. User logs in
2. Email displayed in header
3. Plans load from database
4. Can access plans from any device
5. Click logout to sign out
```

## Configuration

### Environment Variables

```bash
# Required for Authenticated Mode
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key_here
SUPABASE_SERVICE_KEY=your_service_key_here  # Backend only

# Flask Configuration
FLASK_ENV=production
FLASK_DEBUG=0
```

### Docker Deployment

```yaml
services:
  racecraft:
    image: lennon101/racecraft:latest
    environment:
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
      - SUPABASE_SERVICE_KEY=${SUPABASE_SERVICE_KEY}
      - FLASK_ENV=production
```

## Testing

### Testing Anonymous Flow

1. Visit app without Supabase configured
2. Create and save a plan
3. Verify it appears in "Load Plan" list
4. Reload page - plan should still be there
5. Delete plan - should be removed

### Testing Authenticated Flow

1. Configure Supabase credentials
2. Visit app
3. Click "Sign Up" and create account
4. Create and save a plan
5. Log out and log back in
6. Verify plan is still accessible
7. Open app in different browser/device
8. Log in and verify plan syncs

### Testing Migration Flow

1. Visit app with Supabase configured
2. Create plans as anonymous user
3. Click "Sign Up" and create account
4. Verify success message shows plan count
5. Verify all plans are accessible
6. Log out and log back in
7. Verify plans persist

## Troubleshooting

### "Supabase not configured" Message

**Cause**: Environment variables not set or invalid
**Solution**: Ensure `SUPABASE_URL` and `SUPABASE_ANON_KEY` are set correctly

### Plans Not Showing After Login

**Cause**: RLS policies not applied or migration failed
**Solution**: 
1. Check Supabase dashboard for RLS policies
2. Verify migration function exists
3. Check browser console for errors

### Anonymous Plans Not Migrating

**Cause**: Anonymous ID not found or migration function error
**Solution**:
1. Check browser localStorage for `racecraft_anonymous_id`
2. Verify migration endpoint is being called
3. Check backend logs for migration errors

## Future Enhancements

Potential future additions to the authentication system:

- **OAuth Providers**: Google, GitHub, Apple Sign In
- **Email Verification**: Optional email confirmation for new accounts
- **Password Reset**: Forgot password functionality
- **Profile Management**: User profile editing
- **Team/Crew Features**: Shared plans and crew access
- **Subscription Tiers**: Premium features for authenticated users
- **Account Deletion**: GDPR-compliant account deletion

## Conclusion

The RaceCraft authentication system provides a flexible, secure foundation for user data management while maintaining the low-friction anonymous access that makes the app easy to try. The seamless migration from anonymous to authenticated ensures users never lose their data when deciding to create an account.
