# 🔐 Google OAuth Setup Guide

## Quick Setup (5 minutes)

### Step 1: Create Google Cloud Project

1. Go to: https://console.cloud.google.com/
2. Click **"New Project"**
3. Name: `SvidNet Arena`
4. Click **"Create"**

### Step 2: Enable Google OAuth

1. In your project, go to **"APIs & Services" > "OAuth consent screen"**
2. Select **"External"** (for testing)
3. Click **"Create"**

**Fill in:**
- **App name**: `SvidNet Arena`
- **User support email**: Your email
- **Developer contact**: Your email
4. Click **"Save and Continue"**
5. Skip **"Scopes"** (click "Save and Continue")
6. Skip **"Test users"** (click "Save and Continue")
7. Click **"Back to Dashboard"**

### Step 3: Create OAuth Credentials

1. Go to **"APIs & Services" > "Credentials"**
2. Click **"+ Create Credentials" > "OAuth client ID"**
3. Application type: **"Web application"**
4. Name: `SvidNet Arena Web`

**Authorized JavaScript origins:**
```
http://localhost:8000
https://your-app.up.railway.app
```

**Authorized redirect URIs:**
```
http://localhost:8000/api/auth/google/callback
https://your-app.up.railway.app/api/auth/google/callback
```

5. Click **"Create"**

### Step 4: Copy Credentials

You'll see a popup with:
- **Client ID**: `123456789-abcdef.apps.googleusercontent.com`
- **Client Secret**: `GOCSPX-xxxxxxxxxxxxx`

**Copy both!**

### Step 5: Update `.env` File

Edit `backend/.env`:

```env
GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your-client-secret-here
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback
```

### Step 6: Restart Server

```bash
# Stop current server
pkill -f oauth_server.py

# Start OAuth-enabled server
cd backend
python oauth_server.py
```

## ✅ Test It!

1. Open: `http://localhost:3000/oauth-index.html`
2. Click **"Continue with Google"**
3. Sign in with your Google account
4. You'll be redirected back and logged in!

## 🚀 For Railway Deployment

When deploying to Railway, update the redirect URIs:

1. Go back to Google Cloud Console
2. **"APIs & Services" > "Credentials"**
3. Click on your OAuth client ID
4. Add your Railway URL to:
   - **Authorized JavaScript origins**: `https://your-app.up.railway.app`
   - **Authorized redirect URIs**: `https://your-app.up.railway.app/api/auth/google/callback`

5. Update Railway environment variables:
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
   - `GOOGLE_REDIRECT_URI=https://your-app.up.railway.app/api/auth/google/callback`

## 🔒 Security Notes

- **Never commit** `.env` file to git
- **Never share** your Client Secret
- For production, use **"Internal"** OAuth consent screen (requires Google Workspace)
- Keep credentials in environment variables

## 📋 Troubleshooting

**Error: "redirect_uri_mismatch"**
- Make sure the redirect URI in Google Console exactly matches your app's URL
- Include the protocol (http:// or https://)
- No trailing slashes

**OAuth not working?**
- Check that `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set
- Restart the server after updating `.env`
- Clear browser cookies/cache

## 🎉 Done!

Your users can now sign in with Google! This works for both:
- ✅ New users (creates account automatically)
- ✅ Existing users (links Google account to their profile)
