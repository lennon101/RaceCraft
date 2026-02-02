# Supabase Setup Guide

This guide explains how to set up Supabase for RaceCraft authentication and data storage.

## Prerequisites

- A Supabase account (sign up at https://supabase.com)
- A Supabase project created

## Step 1: Get Your Supabase Credentials

1. Go to your Supabase project dashboard
2. Navigate to **Settings** → **API**
3. Copy the following values:
   - **Project URL** (e.g., `https://xxxxx.supabase.co`)
   - **anon/public key** (starts with `eyJ...`)
   - **service_role key** (starts with `eyJ...`, keep this secret!)

## Step 2: Configure Environment Variables

Create a `.env` file in the root directory (or use environment variables in your deployment):

```bash
# Required Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key_here
SUPABASE_SERVICE_KEY=your_service_role_key_here

# Flask Configuration
FLASK_ENV=production
FLASK_DEBUG=0
```

**⚠️ Important**: Never commit the `.env` file to version control. It's already in `.gitignore`.

## Step 3: Run Database Migrations

You have two options to run the migrations:

### Option A: Using Supabase Dashboard (Easiest)

1. Go to your Supabase project dashboard
2. Navigate to **SQL Editor**
3. Create a new query
4. Copy the contents of `supabase/migrations/001_create_user_plans.sql`
5. Paste it into the SQL editor and click **Run**

### Option B: Using Supabase CLI

```bash
# Install Supabase CLI
npm install -g supabase

# Login to Supabase
supabase login

# Link your project
supabase link --project-ref your-project-ref

# Run migrations
supabase db push
```

## Step 4: Verify the Setup

After running the migrations, verify that:

1. The `user_plans` table exists:
   - Go to **Table Editor** in Supabase dashboard
   - You should see a `user_plans` table

2. Row Level Security is enabled:
   - Go to **Authentication** → **Policies**
   - You should see policies for `user_plans` table

## Step 5: Configure Authentication Providers

### Email/Password Authentication (Default)

Email authentication is enabled by default. No additional configuration needed.

### Magic Link (Passwordless)

Magic links are enabled by default but require email configuration:

1. Go to **Authentication** → **Email Templates**
2. Customize the magic link email template (optional)
3. Configure SMTP settings in **Settings** → **Authentication** → **SMTP Settings**

### OAuth Providers (Optional)

To enable OAuth providers like Google, GitHub, or Apple:

1. Go to **Authentication** → **Providers**
2. Enable the provider you want (e.g., Google)
3. Add the required OAuth credentials (Client ID and Secret)
4. Configure the redirect URLs

## Step 6: Test the Application

1. Start the application (locally or via Docker)
2. Open the app in your browser
3. Try the following:
   - Use the app anonymously (should work without login)
   - Click "Sign In" and create an account
   - Save a plan while authenticated
   - Log out and log back in (your plan should still be there)
   - Create anonymous plans and upgrade to an account (plans should migrate)

## Docker Configuration

When deploying with Docker, pass the environment variables:

### Docker Compose

```yaml
services:
  fuel-planner:
    image: lennon101/racecraft:latest
    environment:
      - SUPABASE_URL=https://your-project.supabase.co
      - SUPABASE_ANON_KEY=your_anon_key
      - SUPABASE_SERVICE_KEY=your_service_key
      - FLASK_ENV=production
```

### Docker Run

```bash
docker run -d \
  -e SUPABASE_URL=https://your-project.supabase.co \
  -e SUPABASE_ANON_KEY=your_anon_key \
  -e SUPABASE_SERVICE_KEY=your_service_key \
  -e FLASK_ENV=production \
  -p 5000:5000 \
  lennon101/racecraft:latest
```

## Troubleshooting

### "Supabase not configured" Error

- Ensure `SUPABASE_URL` and `SUPABASE_ANON_KEY` are set
- Check that the environment variables are loaded correctly

### Authentication Fails

- Verify that the migration script ran successfully
- Check that RLS policies are enabled in Supabase dashboard
- Ensure you're using the correct API keys

### Plans Not Showing

- Check browser console for errors
- Verify that the user is authenticated (check session in browser DevTools)
- Ensure RLS policies allow the user to access their plans

### Anonymous Plans Not Migrating

- Verify the migration function exists in Supabase (check **Database** → **Functions**)
- Check that the anonymous session ID is being stored correctly in localStorage
- Look for errors in the backend logs

## Security Considerations

1. **Never expose `service_role` key in frontend code** - it has full database access
2. **Always use `anon` key in frontend** - it respects RLS policies
3. **Keep `.env` file secure** - don't commit it to version control
4. **Use HTTPS in production** - especially important for authentication
5. **Enable email confirmation** (optional but recommended):
   - Go to **Authentication** → **Settings**
   - Enable "Confirm email" for new signups

## Additional Resources

- [Supabase Documentation](https://supabase.com/docs)
- [Row Level Security Guide](https://supabase.com/docs/guides/auth/row-level-security)
- [Supabase Auth Documentation](https://supabase.com/docs/guides/auth)
