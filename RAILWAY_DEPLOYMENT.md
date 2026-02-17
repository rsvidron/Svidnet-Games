# 🚂 Railway Deployment Guide

## Quick Deploy (10 minutes)

### Prerequisites
- GitHub account (you have this! ✅)
- Railway account (free - sign up at railway.app)
- Your code is already pushed to: https://github.com/rsvidron/Svidnet-Games.git

---

## Step 1: Sign Up for Railway

1. Go to: https://railway.app
2. Click **"Login"**
3. Choose **"Login with GitHub"**
4. Authorize Railway

---

## Step 2: Create New Project

1. Click **"New Project"**
2. Select **"Deploy from GitHub repo"**
3. Find and select: **`rsvidron/Svidnet-Games`**
4. Railway will automatically detect it's a Python project

---

## Step 3: Configure Environment Variables

Click on your deployment, then go to **"Variables"** tab.

Add these variables:

```
APP_NAME=SvidNet Game Platform
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=<generate-random-key>
DATABASE_URL=<railway-will-auto-create>
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your-secret
CORS_ORIGINS=["https://your-app.up.railway.app"]
```

**To generate SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## Step 4: Add PostgreSQL Database (Optional)

1. Click **"New"** in your project
2. Select **"Database" > "PostgreSQL"**
3. Railway auto-connects it to your app
4. The `DATABASE_URL` variable is automatically set

For now, **SQLite works fine** (already configured).

---

## Step 5: Deploy!

1. Railway automatically deploys when you push to GitHub
2. Wait 2-3 minutes for build
3. Click **"View Logs"** to see progress
4. When done, click **"Generate Domain"** to get your public URL

---

## Step 6: Update Google OAuth Redirect URIs

Once you have your Railway URL (e.g., `https://svidnet-arena-production.up.railway.app`):

1. Go to Google Cloud Console
2. Update OAuth redirect URIs:
   - Add: `https://your-railway-url.up.railway.app/api/auth/google/callback`

3. Update environment variable on Railway:
   ```
   GOOGLE_REDIRECT_URI=https://your-railway-url.up.railway.app/api/auth/google/callback
   ```

---

## 🎉 You're Live!

Your app will be accessible at:
```
https://your-app.up.railway.app
```

### API Documentation:
```
https://your-app.up.railway.app/docs
```

### Frontend:
```
https://your-app.up.railway.app/oauth-index.html
```

---

## 🔄 Automatic Deployments

Every time you push to GitHub:
1. Railway detects the change
2. Automatically builds and deploys
3. Zero downtime deployment
4. Rollback available if needed

---

## 💰 Pricing

**Free Tier Includes:**
- 500 hours/month execution time
- $5 credit/month
- Perfect for testing and MVP!

**Pro Tier** ($20/month):
- Unlimited execution
- Custom domains
- Better performance

---

## 📊 Monitoring

Railway provides:
- ✅ Real-time logs
- ✅ Metrics (CPU, Memory, Network)
- ✅ Deployment history
- ✅ Easy rollbacks

---

## 🔧 Troubleshooting

**Build fails?**
- Check logs in Railway dashboard
- Ensure `requirements-simple.txt` has all dependencies
- Try "Redeploy" button

**App crashes?**
- Check "Logs" tab for errors
- Verify environment variables are set correctly
- Make sure `SECRET_KEY` is set

**Can't access?**
- Wait 2-3 minutes after deployment
- Check if domain is generated
- Try force HTTPS: `https://your-url.up.railway.app`

---

## 🚀 Alternative: Deploy Button

Create a one-click deploy button:

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template?template=https://github.com/rsvidron/Svidnet-Games)

---

## 📝 Post-Deployment Checklist

- [ ] App is accessible at Railway URL
- [ ] API docs work: `/docs`
- [ ] Health check passes: `/health`
- [ ] Google OAuth configured with new redirect URI
- [ ] Test registration works
- [ ] Test login works
- [ ] Test Google login works
- [ ] Environment variables are secure (no hardcoded secrets)

---

## 🔐 Security Best Practices

1. **Never commit `.env`** - Already in `.gitignore` ✅
2. **Use strong `SECRET_KEY`** - Generate random one
3. **Enable HTTPS** - Railway does this automatically ✅
4. **Set `DEBUG=False`** in production
5. **Restrict CORS** - Only allow your frontend domain

---

## 📈 Scaling

To handle more users:
1. Upgrade to Pro tier
2. Add PostgreSQL database
3. Enable Redis for caching
4. Use Railway's autoscaling

---

Need help? Railway has great documentation and Discord support!
