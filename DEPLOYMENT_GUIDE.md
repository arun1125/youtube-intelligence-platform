# Deployment Guide - YouTube Context Engine

This guide will walk you through deploying your app to **Render** (free tier).

---

## Prerequisites

- [x] GitHub account
- [x] Render account (sign up at https://render.com)
- [x] Your code pushed to GitHub
- [x] Environment variables from your `.env` file

---

## Step 1: Push Code to GitHub

If you haven't already:

```bash
cd /Users/arun/Desktop/00_Organized/Projects/python_projects/youtube-competitive-intelligence

# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Ready for deployment"

# Create a new repo on GitHub, then:
git remote add origin https://github.com/YOUR-USERNAME/youtube-context-engine.git
git branch -M main
git push -u origin main
```

---

## Step 2: Deploy to Render

### 2.1 Create New Web Service

1. Go to https://dashboard.render.com
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub account (if not connected)
4. Find and select your `youtube-context-engine` repository
5. Click **"Connect"**

### 2.2 Configure Build Settings

Render should auto-detect Docker. Verify these settings:

- **Name**: `youtube-context-engine` (or whatever you prefer)
- **Region**: Oregon (US West) - closest free region
- **Branch**: `main`
- **Environment**: `Docker`
- **Instance Type**: `Free`

### 2.3 Add Environment Variables

Click **"Advanced"** → **"Add Environment Variable"**

Add each of these (copy values from your `.env` file):

**Copy all values from your `.env` file. DO NOT commit real keys to git!**

Example format (replace with your actual values in Render dashboard):

```
SUPABASE_URL = your_supabase_url_here
SUPABASE_PUBLISHABLE_KEY = your_supabase_publishable_key
SUPABASE_SECRET_KEY = your_supabase_secret_key

GOOGLE_API_KEY = your_google_api_key
GEMINI_API_KEY = your_gemini_api_key

GOOGLE_CLIENT_ID = your_google_client_id
GOOGLE_CLIENT_SECRET = your_google_client_secret
GOOGLE_REDIRECT_URI = http://localhost:8000/auth/callback

STRIPE_SECRET_KEY = your_stripe_secret_key
STRIPE_PUBLISHABLE_KEY = your_stripe_publishable_key
STRIPE_PRICE_ID_PRO = your_stripe_price_id
STRIPE_WEBHOOK_SECRET = your_stripe_webhook_secret
```

*Note: Get your actual values from your local `.env` file*

**App Settings:**
```
DEBUG = false
APP_NAME = YouTube Context Engine
APP_VERSION = 1.0.0
```

### 2.4 Deploy!

1. Click **"Create Web Service"**
2. Render will start building your Docker image
3. Wait 5-10 minutes for the build to complete
4. You'll see "Your service is live 🎉"

**Copy your production URL**: `https://youtube-context-engine.onrender.com`

---

## Step 3: Test Basic Deployment

1. Visit your Render URL: `https://youtube-context-engine.onrender.com`
2. You should see your homepage load
3. Check health endpoint: `https://youtube-context-engine.onrender.com/health`
   - Should return: `{"status":"healthy","app":"YouTube Context Engine","version":"1.0.0"}`

**If you see errors**, check Render logs:
- Go to your service dashboard
- Click "Logs" tab
- Look for error messages

---

## Step 4: Configure Google OAuth

Now that you have a production URL, update Google OAuth settings:

### 4.1 Update Google Cloud Console

1. Go to https://console.cloud.google.com
2. Select your project
3. Navigate to **"APIs & Services"** → **"Credentials"**
4. Click on your OAuth 2.0 Client ID
5. Under **"Authorized redirect URIs"**, click **"+ ADD URI"**
6. Add: `https://youtube-context-engine.onrender.com/auth/callback`
   - Replace `youtube-context-engine` with your actual Render app name
7. Click **"Save"**

### 4.2 Update Render Environment Variable

1. Go back to Render dashboard
2. Click on your service
3. Go to **"Environment"** tab
4. Find `GOOGLE_REDIRECT_URI`
5. Update value to: `https://youtube-context-engine.onrender.com/auth/callback`
6. Click **"Save Changes"**
7. Render will automatically redeploy (wait ~2 minutes)

### 4.3 Test Login

1. Visit your production URL
2. Click **"Sign in with Google"**
3. You should be redirected to Google login
4. After login, you should return to your dashboard
5. ✅ If you see your dashboard, OAuth is working!

---

## Step 5: Configure Stripe Webhook (Before Accepting Payments)

**IMPORTANT:** Only do this when you're ready to accept real payments.

### 5.1 Create Webhook Endpoint in Stripe

1. Go to https://dashboard.stripe.com/webhooks
2. Click **"Add endpoint"**
3. Enter endpoint URL: `https://youtube-context-engine.onrender.com/api/payment/webhook`
4. Click **"Select events"**, choose:
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
5. Click **"Add endpoint"**

### 5.2 Get Webhook Secret

1. Click on the webhook you just created
2. Under **"Signing secret"**, click **"Reveal"**
3. Copy the secret (starts with `whsec_`)

### 5.3 Update Render Environment Variable

1. Go to Render dashboard → Your service → Environment tab
2. Find `STRIPE_WEBHOOK_SECRET`
3. Update value with the new secret you copied
4. Click **"Save Changes"**
5. Wait for automatic redeploy

### 5.4 Test Webhook

1. In Stripe Dashboard, go to your webhook
2. Click **"Send test webhook"**
3. Select `checkout.session.completed`
4. Click **"Send test webhook"**
5. You should see a **200 OK** response

---

## Step 6: Update CORS Settings (Important!)

After deployment, update your CORS settings to lock down security:

1. Open `app/main.py` locally
2. Find line 42: `"https://your-app-name.onrender.com"`
3. Replace with your actual URL: `"https://youtube-context-engine.onrender.com"`
4. Commit and push:
   ```bash
   git add app/main.py
   git commit -m "Update CORS for production"
   git push
   ```
5. Render will auto-deploy the update

---

## Step 7: Run Database Migrations

Your Supabase database needs these migrations:

### 7.1 Run Initial Schema

1. Go to your Supabase project: https://supabase.com/dashboard/project/YOUR_PROJECT_ID
2. Click **"SQL Editor"**
3. Click **"New query"**
4. Copy contents of `supabase/migrations/001_initial_schema.sql`
5. Paste and click **"Run"**

### 7.2 Add Subscription Status

1. Still in SQL Editor, click **"New query"**
2. Copy contents of `supabase/migrations/002_add_subscription_status.sql`
3. Paste and click **"Run"**

### 7.3 Add Shotlist Tables

1. Still in SQL Editor, click **"New query"**
2. Copy contents of `supabase/migrations/003_add_shotlist_tables.sql`
3. Paste and click **"Run"**

### 7.4 Add Increment Function

1. Still in SQL Editor, click **"New query"**
2. Copy contents of `add_increment_function.sql`
3. Paste and click **"Run"**

### 7.5 Verify Tables Exist

Run this query to verify:
```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
```

You should see:
- `profiles`
- `thumbnail_tests`
- `test_videos`
- `user_api_keys`
- `production_projects`
- `production_videos`
- `production_shots`

---

## Step 8: Final Testing

Run through these scenarios:

### Test 1: Homepage Loads
- ✅ Visit your production URL
- ✅ Homepage displays correctly
- ✅ No console errors

### Test 2: Login Works
- ✅ Click "Sign in with Google"
- ✅ Redirected to Google
- ✅ After login, returns to dashboard
- ✅ Dashboard shows user info

### Test 3: Create Test
- ✅ Click "Create New Test"
- ✅ Fill form and submit
- ✅ Video grid displays
- ✅ Your thumbnail appears in grid
- ✅ Check Supabase: test saved in `thumbnail_tests` table
- ✅ Check Supabase: videos saved in `test_videos` table

### Test 4: Usage Tracking
- ✅ Dashboard shows "1 / 5 tests used"
- ✅ Create 4 more tests
- ✅ Dashboard shows "5 / 5 tests used"
- ✅ Try to create 6th test → blocked with error

### Test 5: Payment Flow (Optional - only if ready)
- ✅ Click "Upgrade to Pro"
- ✅ Redirected to Stripe checkout
- ⚠️ Don't actually pay yet (use Stripe test mode)
- ✅ Use test card: `4242 4242 4242 4242`
- ✅ Complete checkout
- ✅ Webhook fires and updates user to Pro
- ✅ Dashboard shows "Pro" tier

---

## Troubleshooting

### Issue: "Application Error" on Render

**Check:**
- Render logs for specific error message
- All environment variables are set correctly
- No typos in variable names

### Issue: Login doesn't work / OAuth error

**Check:**
- `GOOGLE_REDIRECT_URI` matches your Render URL exactly
- Google Cloud Console has the redirect URI whitelisted
- No trailing slashes in URLs

### Issue: Database errors

**Check:**
- All migrations ran successfully in Supabase
- Supabase URL/keys are correct
- RLS policies are set up (from migrations)

### Issue: Uploads don't persist

**Expected behavior on free tier:**
- Render's free tier has ephemeral storage
- Uploaded files will be deleted when app restarts
- For production, use S3/Cloudinary for file storage

### Issue: App is slow / times out

**Free tier limitations:**
- App spins down after 15 minutes of inactivity
- First request after spin-down takes 30-60 seconds (cold start)
- Upgrade to paid tier ($7/mo) to keep app always on

---

## What's Next?

### Immediate:
- [ ] Share your app with friends for testing
- [ ] Monitor Render logs for errors
- [ ] Watch Supabase for usage patterns

### Before Launching:
- [ ] Set up file storage (S3/Cloudinary) for uploads
- [ ] Add error monitoring (Sentry)
- [ ] Set up analytics (Google Analytics/Plausible)
- [ ] Create privacy policy & terms of service
- [ ] Test payment flow thoroughly in test mode

### When Ready to Accept Payments:
- [ ] Switch Stripe to live mode (not test mode)
- [ ] Update Stripe keys in Render
- [ ] Reconfigure webhook for live mode
- [ ] Test payment with real card (then refund yourself)

---

## Support

**If you get stuck:**
- Check Render logs first
- Check Supabase logs
- Review this guide step-by-step
- Check environment variables are correct

**Common gotchas:**
- Forgetting to update `GOOGLE_REDIRECT_URI`
- Not running database migrations
- Typos in environment variable names
- Using wrong Stripe keys (test vs live)

---

## Your Production URLs

After deployment, save these:

- **App**: https://youtube-context-engine.onrender.com
- **Health Check**: https://youtube-context-engine.onrender.com/health
- **Dashboard**: https://youtube-context-engine.onrender.com/dashboard
- **Webhook**: https://youtube-context-engine.onrender.com/api/payment/webhook

---

**You're ready to deploy! 🚀**

Start with Step 1 and work through each step carefully. Good luck!
