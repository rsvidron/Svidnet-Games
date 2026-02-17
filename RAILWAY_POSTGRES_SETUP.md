# Railway PostgreSQL Setup Guide

This guide shows how to add PostgreSQL to your Railway project so user data persists across deploys.

## Why PostgreSQL?

Railway has an **ephemeral filesystem** - files are reset on every deploy. SQLite stores data in a file, so all users, games, and scores are lost on each deploy. PostgreSQL is a separate service with persistent storage.

## Step 1: Add PostgreSQL to Railway Project

1. Go to your Railway project dashboard: https://railway.app/project/your-project-id
2. Click **"New"** → **"Database"** → **"Add PostgreSQL"**
3. Railway will automatically:
   - Provision a PostgreSQL database
   - Add a `DATABASE_URL` environment variable to your service
   - The variable is automatically available to your backend

## Step 2: Verify Environment Variable

1. In Railway, click on your **backend service**
2. Go to the **"Variables"** tab
3. You should see `DATABASE_URL` with a value like:
   ```
   postgresql://postgres:password@containers.railway.app:5432/railway
   ```
4. **No action needed** - this is automatically set when you add PostgreSQL

## Step 3: Deploy

The code already supports PostgreSQL via the `DATABASE_URL` environment variable:

- If `DATABASE_URL` exists → uses PostgreSQL ✅
- If not → falls back to SQLite (local development)

Just push your code:

```bash
git push origin main
```

Railway will:
1. Detect the PostgreSQL database
2. Use `DATABASE_URL` to connect
3. Create all tables automatically on first run
4. Data persists across all future deploys

## Step 4: Verify It Works

After deploy:

1. Register a new user
2. Redeploy the app (push a small change)
3. Try logging in with the same credentials
4. ✅ If login works, PostgreSQL is working!

## Database Management

### View Database Contents

In Railway dashboard:
1. Click on the **PostgreSQL** service
2. Go to **"Data"** tab
3. You can run SQL queries to view your data

### Connect with psql (optional)

Railway provides connection details in the PostgreSQL service:
- Host
- Port
- Username
- Password
- Database name

Use these to connect with `psql` or any PostgreSQL client.

## Troubleshooting

### "Could not connect to database"

- Check that PostgreSQL service is running in Railway
- Verify `DATABASE_URL` is set in your backend service variables
- Check Railway logs for connection errors

### "Tables don't exist"

The app creates tables automatically via SQLAlchemy:
```python
Base.metadata.create_all(bind=engine)
```

If tables aren't created:
- Check logs for errors during startup
- Ensure all model files are imported in `oauth_server.py`

### Need to reset database?

In Railway PostgreSQL service:
1. Go to **"Settings"** tab
2. Scroll to **"Danger Zone"**
3. Click **"Reset Database"** (WARNING: deletes all data)

## Cost

Railway PostgreSQL:
- **Starter Plan**: $5/month for 512MB database
- **Free Trial**: Includes some free database usage

Check Railway pricing: https://railway.app/pricing
