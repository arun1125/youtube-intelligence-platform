-- Add subscription_status column for Stripe subscription tracking
-- Run this in Supabase SQL Editor

ALTER TABLE profiles
ADD COLUMN IF NOT EXISTS subscription_status TEXT DEFAULT 'active'
CHECK (subscription_status IN ('active', 'canceled', 'past_due', 'trialing', 'incomplete', 'incomplete_expired', 'unpaid'));

COMMENT ON COLUMN profiles.subscription_status IS 'Stripe subscription status (synced via webhooks)';

-- Update existing free tier users to have 'active' status
UPDATE profiles
SET subscription_status = 'active'
WHERE subscription_status IS NULL;

SELECT 'Subscription status column added successfully! ✓' AS status;
