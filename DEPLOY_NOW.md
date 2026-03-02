# 🚀 Deploy Page Access Control System

## Quick Deploy Steps

All changes are committed and ready to push. Follow these steps:

### Step 1: Push to GitHub

From your **local machine** or any environment with GitHub access:

```bash
cd /path/to/Svidnet-Games

# Pull the latest commit from this workspace
git fetch origin main
git pull origin main

# Or if you're already on this branch, just push:
git push origin main
```

**The commit is already made:**
- Commit: `7791fe5`
- Message: "Add comprehensive page access control system"

### Step 2: Railway Auto-Deploy

Railway will automatically detect the push and start deploying. You can monitor it at:
- https://railway.app/project/your-project

The deployment should take 2-5 minutes.

### Step 3: Run Database Migration

Once the backend is deployed, you need to apply the database migration:

#### Option A: From Railway Dashboard (Recommended)

1. Go to Railway dashboard
2. Click on your **PostgreSQL** service
3. Click **"Data"** or **"Query"** tab
4. Run this SQL:

```sql
-- Create page_access table
CREATE TABLE IF NOT EXISTS page_access (
    id SERIAL PRIMARY KEY,
    page_name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    allowed_roles TEXT[] DEFAULT ARRAY['admin']::TEXT[],
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_page_access_page_name ON page_access(page_name);
CREATE INDEX IF NOT EXISTS idx_page_access_active ON page_access(is_active);

-- Insert default pages
INSERT INTO page_access (page_name, display_name, allowed_roles, description) VALUES
('sportsbook', 'Sportsbook', ARRAY['admin']::TEXT[], 'Sports betting and predictions page'),
('wordle', 'Wordle', ARRAY['basic', 'user', 'admin']::TEXT[], 'Daily and endless Wordle games'),
('wrestling', 'Wrestling', ARRAY['user', 'admin']::TEXT[], 'Wrestling-themed games and content'),
('trivia-game', 'Trivia Game', ARRAY['basic', 'user', 'admin']::TEXT[], 'Trivia game modes'),
('movies', 'Movies', ARRAY['basic', 'user', 'admin']::TEXT[], 'Movie-related games and leaderboards'),
('dashboard', 'Dashboard', ARRAY['basic', 'user', 'admin']::TEXT[], 'User dashboard'),
('profile', 'Profile', ARRAY['basic', 'user', 'admin']::TEXT[], 'User profile page'),
('rankings', 'Rankings', ARRAY['basic', 'user', 'admin']::TEXT[], 'Global rankings and leaderboards'),
('admin', 'Admin Panel', ARRAY['admin']::TEXT[], 'Admin panel for managing the platform')
ON CONFLICT (page_name) DO NOTHING;

-- Add trigger to auto-update updated_at
CREATE TRIGGER update_page_access_updated_at BEFORE UPDATE ON page_access
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Update users table role check constraint
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check;
ALTER TABLE users ADD CONSTRAINT users_role_check CHECK (role IN ('basic', 'user', 'admin'));
```

#### Option B: From Railway CLI

```bash
railway login
railway link
railway run psql $DATABASE_URL -f backend/migrations/add_page_access_control.sql
```

#### Option C: From Backend Service Shell

1. Go to Railway dashboard
2. Click on your **Backend** service
3. Click **"Settings"** → **"Service"** → **"Shell"**
4. Run:

```bash
python << 'EOF'
import asyncio
from sqlalchemy import text
from app.db.session import get_async_db

async def run_migration():
    async for db in get_async_db():
        with open('/app/backend/migrations/add_page_access_control.sql', 'r') as f:
            sql = f.read()
        await db.execute(text(sql))
        await db.commit()
        print("Migration completed!")

asyncio.run(run_migration())
EOF
```

### Step 4: Verify Deployment

1. **Check Railway logs** to ensure no errors
2. **Visit your app** and log in as admin
3. **Navigate to Admin Panel** → Click **"🔒 Page Access"** tab
4. **You should see all pages** with their permission configurations

### Step 5: Test Access Control

1. Log in as an **admin user**
   - Should be able to access Sportsbook ✅

2. Log in as a **regular user** (role='user')
   - Should be able to access Wrestling ✅
   - Should NOT be able to access Sportsbook ❌

3. Log in as a **basic user** (role='basic')
   - Should be able to access Wordle ✅
   - Should NOT be able to access Wrestling or Sportsbook ❌

## Troubleshooting

### Migration Fails

If the migration fails, check:
- Is the `update_updated_at_column()` function already created?
- Does the `page_access` table already exist?
- Run each SQL statement separately to find the issue

### Can't Access Admin Panel

If you can't see the Page Access tab:
- Clear browser cache
- Hard refresh (Ctrl+Shift+R or Cmd+Shift+R)
- Check browser console for JavaScript errors

### API_URL Issues

The frontend currently uses `http://localhost:8000`. For production:

1. Find all instances in the frontend files
2. Replace with your Railway backend URL:
   ```javascript
   const API_URL = 'https://your-backend.railway.app';
   ```

Or better, create a config file:

```javascript
// frontend/config.js
const API_URL = window.location.hostname === 'localhost'
    ? 'http://localhost:8000'
    : 'https://your-backend.railway.app';
```

## What Will Change After Deployment

✅ New **"Page Access"** tab in Admin Panel
✅ Sportsbook restricted to admin only
✅ Wrestling accessible to user role and above
✅ Wordle accessible to basic role and above
✅ Access denied page for unauthorized access
✅ Admin API endpoints for managing permissions

## Update User Roles (If Needed)

To change user roles after deployment:

```sql
-- Make a user admin
UPDATE users SET role = 'admin' WHERE username = 'yourusername';

-- Make a user standard user
UPDATE users SET role = 'user' WHERE username = 'someuser';

-- Make a user basic
UPDATE users SET role = 'basic' WHERE username = 'basicuser';
```

---

## Summary

1. ✅ Code is committed
2. 🔄 Push to GitHub: `git push origin main`
3. 🚂 Railway auto-deploys
4. 🗄️ Run database migration
5. ✨ Test the new admin interface

**You're all set!** The page access control system is ready to deploy.
