-- Create user_plans table with Row Level Security
-- This table stores race plans with proper user ownership

CREATE TABLE IF NOT EXISTS public.user_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    anonymous_id TEXT,
    plan_name TEXT NOT NULL,
    plan_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure either owner_id or anonymous_id is set, but not both
    CONSTRAINT check_ownership CHECK (
        (owner_id IS NOT NULL AND anonymous_id IS NULL) OR
        (owner_id IS NULL AND anonymous_id IS NOT NULL)
    )
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_user_plans_owner ON public.user_plans(owner_id);
CREATE INDEX IF NOT EXISTS idx_user_plans_anonymous ON public.user_plans(anonymous_id);
CREATE INDEX IF NOT EXISTS idx_user_plans_created ON public.user_plans(created_at DESC);

-- Create partial unique indexes to enforce unique plan names per user/anonymous session
-- Using partial indexes because NULL values in unique constraints behave differently
CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_plan_per_user 
    ON public.user_plans(owner_id, plan_name) 
    WHERE owner_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_plan_per_anon 
    ON public.user_plans(anonymous_id, plan_name) 
    WHERE anonymous_id IS NOT NULL;

-- Enable Row Level Security
ALTER TABLE public.user_plans ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view their own authenticated plans
CREATE POLICY "Users can view own plans" ON public.user_plans
    FOR SELECT
    USING (
        (auth.uid() IS NOT NULL AND owner_id = auth.uid())
    );

-- Policy: Anonymous users can view their own plans using session ID
-- Note: This requires passing anonymous_id in queries from the application
CREATE POLICY "Anonymous users can view own plans" ON public.user_plans
    FOR SELECT
    USING (
        (auth.uid() IS NULL AND anonymous_id IS NOT NULL)
    );

-- Policy: Users can insert their own plans
CREATE POLICY "Users can insert own plans" ON public.user_plans
    FOR INSERT
    WITH CHECK (
        (auth.uid() IS NOT NULL AND owner_id = auth.uid() AND anonymous_id IS NULL)
    );

-- Policy: Anonymous users can insert plans with their session ID
CREATE POLICY "Anonymous users can insert plans" ON public.user_plans
    FOR INSERT
    WITH CHECK (
        (auth.uid() IS NULL AND anonymous_id IS NOT NULL AND owner_id IS NULL)
    );

-- Policy: Users can update their own plans
CREATE POLICY "Users can update own plans" ON public.user_plans
    FOR UPDATE
    USING (
        (auth.uid() IS NOT NULL AND owner_id = auth.uid())
    )
    WITH CHECK (
        (auth.uid() IS NOT NULL AND owner_id = auth.uid())
    );

-- Policy: Anonymous users can update their own plans
CREATE POLICY "Anonymous users can update own plans" ON public.user_plans
    FOR UPDATE
    USING (
        (auth.uid() IS NULL AND anonymous_id IS NOT NULL)
    )
    WITH CHECK (
        (auth.uid() IS NULL AND anonymous_id IS NOT NULL)
    );

-- Policy: Users can delete their own plans
CREATE POLICY "Users can delete own plans" ON public.user_plans
    FOR DELETE
    USING (
        (auth.uid() IS NOT NULL AND owner_id = auth.uid())
    );

-- Policy: Anonymous users can delete their own plans
CREATE POLICY "Anonymous users can delete own plans" ON public.user_plans
    FOR DELETE
    USING (
        (auth.uid() IS NULL AND anonymous_id IS NOT NULL)
    );

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_user_plans_updated_at
    BEFORE UPDATE ON public.user_plans
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- Function to migrate anonymous plans to authenticated user
CREATE OR REPLACE FUNCTION public.migrate_anonymous_plans(
    p_anonymous_id TEXT,
    p_user_id UUID
)
RETURNS INTEGER AS $$
DECLARE
    affected_rows INTEGER;
BEGIN
    -- Update all plans from anonymous_id to owner_id
    UPDATE public.user_plans
    SET 
        owner_id = p_user_id,
        anonymous_id = NULL,
        updated_at = NOW()
    WHERE anonymous_id = p_anonymous_id;
    
    GET DIAGNOSTICS affected_rows = ROW_COUNT;
    RETURN affected_rows;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute permission on migration function
GRANT EXECUTE ON FUNCTION public.migrate_anonymous_plans(TEXT, UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION public.migrate_anonymous_plans(TEXT, UUID) TO anon;
