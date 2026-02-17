# 🔧 Railway Deployment Troubleshooting

## Issue Timeline & Fixes

### ❌ Error 1: "pip: command not found" (First Attempt)
**Cause:** Railway's default buildCommand didn't have pip in PATH

**Failed Fix Attempt:**
```toml
[phases.setup]
nixPkgs = ['python311', 'pip']  # ❌ WRONG - 'pip' is not a Nix package
```

### ❌ Error 2: "undefined variable 'pip'" (Second Attempt)
**Cause:** Tried to reference 'pip' as a standalone Nix package, but pip comes bundled with Python

**Failed Fix Attempt:**
```toml
[phases.setup]
nixPkgs = ['python311']  # ✓ Correct

[phases.install]
cmds = ['pip install -r requirements.txt']  # ❌ Still fails - pip not in PATH
```

### ✅ Current Fix (Third Attempt)
**Solution:** Use Python module syntax to invoke pip directly

```toml
[phases.setup]
nixPkgs = ['python311']

[phases.install]
cmds = [
    'python -m pip install --upgrade pip',  # Ensure pip is available via python
    'python -m pip install -r requirements.txt'
]

[start]
cmd = 'cd backend && python oauth_server.py'
```

**Why this works:**
- `python -m pip` invokes pip as a Python module, not a shell command
- This works even when pip isn't in PATH
- Python 3.11 from Nix includes pip by default as a module

## Alternative Solutions (If This Still Fails)

### Option A: Use venv approach
```toml
[phases.setup]
nixPkgs = ['python311']

[phases.install]
cmds = [
    'python -m venv /opt/venv',
    '. /opt/venv/bin/activate && pip install -r requirements.txt'
]

[start]
cmd = '. /opt/venv/bin/activate && cd backend && python oauth_server.py'
```

### Option B: Delete nixpacks.toml and use Procfile only
Let Railway auto-detect Python and manage the build:
```bash
# Just keep Procfile:
web: cd backend && python oauth_server.py
```

### Option C: Use Railway's Python buildpack directly
Delete nixpacks.toml entirely and let Railway detect Python from requirements.txt automatically.

## Current Status
Testing fix with `python -m pip` approach. If this fails, we'll try Option C (remove nixpacks.toml entirely).

## Environment Variables Needed After Deploy
Once deployment succeeds, set these in Railway:

```bash
SECRET_KEY=<generate with: openssl rand -hex 32>
GOOGLE_CLIENT_ID=<from Google Cloud Console>
GOOGLE_CLIENT_SECRET=<from Google Cloud Console>
GOOGLE_REDIRECT_URI=https://your-app.railway.app/api/auth/google/callback
ENVIRONMENT=production
DEBUG=False
DATABASE_URL=<optional - will use SQLite if not set>
```

## Google OAuth Setup
1. Go to https://console.cloud.google.com/apis/credentials
2. Create OAuth 2.0 Client ID
3. Add authorized redirect URI: `https://your-app.railway.app/api/auth/google/callback`
4. Copy Client ID and Secret to Railway environment variables
