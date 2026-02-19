"""
Enhanced API with Google OAuth support
"""
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, timedelta, timezone
from jose import jwt
from passlib.context import CryptContext
from authlib.integrations.starlette_client import OAuth
import os
import httpx

# Import shared database configuration
from database import Base, engine, SessionLocal

# Import user models
from models.user import User, UserProfile

# Import trivia models BEFORE creating tables so they register with Base
try:
    from models.trivia import TriviaGame, TriviaAnswer, TriviaLeaderboard
    print("✓ Trivia models imported successfully")
except ImportError as e:
    print(f"⚠ Trivia models not available: {e}")

# Import friends model
try:
    from models.friends import Friendship
    print("✓ Friends model imported successfully")
except ImportError as e:
    print(f"⚠ Friends model not available: {e}")

# Import admin models
try:
    from models.admin import TriviaCategory, CustomTriviaQuestion, WordleWord
    print("✓ Admin models imported successfully")
except ImportError as e:
    print(f"⚠ Admin models not available: {e}")

# Import links model
try:
    from models.links import Link
    print("✓ Links model imported successfully")
except ImportError as e:
    print(f"⚠ Links model not available: {e}")

# Import Wordle models
try:
    from models.wordle import WordleGame, WordleStats, DailyWordleLeaderboard
    print("✓ Wordle models imported successfully")
except ImportError as e:
    print(f"⚠ Wordle models not available: {e}")

# Import Sports models
try:
    from models.sports import SportsMatch, Bet, BetPick, SportsLeaderboard
    from models.sync_metadata import SyncMetadata
    print("✓ Sports models imported successfully")
except ImportError as e:
    print(f"⚠ Sports models not available: {e}")

# Import Media Review model
try:
    from models.media_review import MediaReview
    print("✓ MediaReview model imported successfully")
except ImportError as e:
    print(f"⚠ MediaReview model not available: {e}")

# Import Ranked List models
try:
    from models.ranked_list import RankedList, RankedListItem
    print("✓ RankedList models imported successfully")
except ImportError as e:
    print(f"⚠ RankedList models not available: {e}")

# Import Collection models
try:
    from models.collection import Collection, CollectionItem
    print("✓ Collection models imported successfully")
except ImportError as e:
    print(f"⚠ Collection models not available: {e}")

# Run Wordle table migration (if needed)
try:
    from migrate_wordle_tables import migrate_wordle_tables
    migrate_wordle_tables()
except Exception as e:
    print(f"⚠ Wordle migration skipped: {e}")

# Create all tables (User, UserProfile, Trivia, Friends, Admin, and Wordle tables)
Base.metadata.create_all(bind=engine)
print(f"✓ Database tables created: {list(Base.metadata.tables.keys())}")

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY", "test-secret-key-for-development")
ALGORITHM = "HS256"

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=24)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Schemas
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict

# FastAPI app
app = FastAPI(title="Svidhaus Arena", version="1.0.0")

# Session middleware (required for OAuth)
SESSION_SECRET = os.getenv("SECRET_KEY", "test-secret-key-for-development-only")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OAuth setup
oauth = OAuth()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    oauth.register(
        name='google',
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )

@app.get("/")
def root():
    """Serve the dashboard (home page)"""
    dashboard_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "dashboard.html")
    if os.path.exists(dashboard_path):
        return FileResponse(dashboard_path)
    return {"message": "Svidhaus Arena", "status": "running"}

@app.get("/login")
def login_page():
    """Serve the login/register page"""
    frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "oauth-index.html")
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return {"message": "Login page not found"}

@app.get("/profile")
def profile_page():
    """Serve the profile page"""
    profile_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "profile.html")
    if os.path.exists(profile_path):
        return FileResponse(profile_path)
    raise HTTPException(404, "Profile page not found")

@app.get("/admin")
def admin_page():
    """Serve the admin panel"""
    admin_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "admin.html")
    if os.path.exists(admin_path):
        return FileResponse(admin_path)
    raise HTTPException(404, "Admin page not found")

@app.get("/wordle")
def wordle_page():
    """Serve the Wordle game page"""
    wordle_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "wordle.html")
    if os.path.exists(wordle_path):
        return FileResponse(wordle_path)
    raise HTTPException(404, "Wordle page not found")

@app.get("/trivia")
def trivia_game():
    """Serve the trivia game HTML"""
    trivia_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "trivia-game.html")
    if os.path.exists(trivia_path):
        return FileResponse(trivia_path)
    raise HTTPException(404, "Trivia game not found")

@app.get("/sportsbook.html")
def sportsbook_page():
    """Serve the sportsbook page"""
    sportsbook_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "sportsbook.html")
    if os.path.exists(sportsbook_path):
        return FileResponse(sportsbook_path)
    raise HTTPException(404, "Sportsbook page not found")

@app.get("/sportsbook")
def sportsbook():
    """Serve the sportsbook page"""
    sportsbook_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "sportsbook.html")
    if os.path.exists(sportsbook_path):
        return FileResponse(sportsbook_path)
    raise HTTPException(404, "Sportsbook page not found")

@app.get("/links")
def links_page():
    """Serve the links dashboard page"""
    links_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "links.html")
    if os.path.exists(links_path):
        return FileResponse(links_path)
    raise HTTPException(404, "Links page not found")

@app.get("/movies")
def movies_page():
    """Serve the movies & TV review page"""
    movies_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "movies.html")
    if os.path.exists(movies_path):
        return FileResponse(movies_path)
    raise HTTPException(404, "Movies page not found")

@app.get("/rankings")
def rankings_page():
    """Redirect to the combined movies & TV page"""
    return RedirectResponse(url="/movies")

@app.get("/health")
def health():
    user_count = SessionLocal().query(User).count()
    oauth_count = SessionLocal().query(User).filter(User.auth_provider == "google").count()
    return {
        "status": "healthy",
        "database": "connected",
        "total_users": user_count,
        "google_users": oauth_count,
        "oauth_configured": bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)
    }

@app.get("/debug")
def debug_info():
    """Debug endpoint to check system status and configuration"""
    import sys
    from sqlalchemy import inspect
    from database import DATABASE_URL

    # Check database tables
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    # Check trivia models import
    trivia_models_loaded = False
    trivia_import_error = None
    try:
        from models.trivia import TriviaGame, TriviaAnswer, TriviaLeaderboard
        trivia_models_loaded = True
    except Exception as e:
        trivia_import_error = str(e)

    # Check trivia router
    trivia_router_loaded = False
    trivia_router_error = None
    try:
        from routers.trivia import router as trivia_router
        trivia_router_loaded = True
    except Exception as e:
        trivia_router_error = str(e)

    # Get sample data from DB
    db = SessionLocal()
    try:
        user_count = db.query(User).count()
        if "trivia_games" in tables:
            from sqlalchemy import text
            trivia_game_count = db.execute(text("SELECT COUNT(*) FROM trivia_games")).scalar()
        else:
            trivia_game_count = "table not found"
    except Exception as e:
        user_count = f"error: {e}"
        trivia_game_count = f"error: {e}"
    finally:
        db.close()

    return {
        "status": "debug_info",
        "python_version": sys.version,
        "database": {
            "url": DATABASE_URL,
            "tables": tables,
            "user_count": user_count,
            "trivia_game_count": trivia_game_count,
        },
        "models": {
            "trivia_models_loaded": trivia_models_loaded,
            "trivia_import_error": trivia_import_error,
            "base_tables": list(Base.metadata.tables.keys()),
        },
        "routers": {
            "trivia_router_loaded": trivia_router_loaded,
            "trivia_router_error": trivia_router_error,
        },
        "environment": {
            "gemini_api_key_set": bool(os.getenv("GEMINI_API_KEY")),
            "google_oauth_configured": bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET),
            "secret_key_set": bool(os.getenv("SECRET_KEY")),
        },
        "api_routes": [
            {"path": route.path, "name": route.name, "methods": list(route.methods) if hasattr(route, 'methods') else []}
            for route in app.routes
            if hasattr(route, 'path')
        ]
    }

@app.post("/api/auth/register", response_model=TokenResponse, status_code=201)
def register(data: UserRegister, db: Session = Depends(get_db)):
    """Register new user (traditional)"""

    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(400, "Username already exists")

    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(400, "Email already exists")

    user = User(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
        role="user",
        is_active=True,
        auth_provider="local"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    profile = UserProfile(user_id=user.id, elo_rating=1200)
    db.add(profile)
    db.commit()

    access_token = create_token({"sub": str(user.id), "username": user.username})
    refresh_token = create_token({"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "avatar_url": user.avatar_url,
            "auth_provider": user.auth_provider
        }
    )

@app.post("/api/auth/login", response_model=TokenResponse)
def login(data: UserLogin, db: Session = Depends(get_db)):
    """Login user (traditional)"""

    user = db.query(User).filter(User.username == data.username).first()
    if not user:
        print(f"Login failed: user '{data.username}' not found")
        raise HTTPException(401, "Invalid username or password")
    if not user.hashed_password:
        print(f"Login failed: user '{data.username}' has no password (OAuth-only account)")
        raise HTTPException(401, "Invalid username or password - try Google Sign-In")
    if not verify_password(data.password, user.hashed_password):
        print(f"Login failed: wrong password for user '{data.username}'")
        raise HTTPException(401, "Invalid username or password")

    if not user.is_active:
        raise HTTPException(403, "Account is inactive")

    access_token = create_token({"sub": str(user.id), "username": user.username})
    refresh_token = create_token({"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "avatar_url": user.avatar_url,
            "auth_provider": user.auth_provider
        }
    )

@app.get("/api/auth/google/login")
async def google_login(request: Request):
    """Initiate Google OAuth login"""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(500, "Google OAuth not configured")

    redirect_uri = request.url_for('google_callback')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.get("/api/auth/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """Handle Google OAuth callback"""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(500, "Google OAuth not configured")

    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')

        if not user_info:
            raise HTTPException(400, "Could not get user info from Google")

        google_id = user_info.get('sub')
        email = user_info.get('email')
        name = user_info.get('name', email.split('@')[0])
        picture = user_info.get('picture')

        # Check if user exists
        user = db.query(User).filter(User.google_id == google_id).first()

        if not user:
            # Check if email exists
            existing_user = db.query(User).filter(User.email == email).first()
            if existing_user:
                # Link Google account to existing user
                existing_user.google_id = google_id
                existing_user.avatar_url = picture
                existing_user.auth_provider = "google"
                db.commit()
                user = existing_user
            else:
                # Create new user
                username = name.replace(" ", "").lower()
                # Ensure unique username
                counter = 1
                base_username = username
                while db.query(User).filter(User.username == username).first():
                    username = f"{base_username}{counter}"
                    counter += 1

                user = User(
                    username=username,
                    email=email,
                    google_id=google_id,
                    avatar_url=picture,
                    role="user",
                    is_active=True,
                    auth_provider="google"
                )
                db.add(user)
                db.commit()
                db.refresh(user)

                # Create profile
                profile = UserProfile(user_id=user.id, elo_rating=1200)
                db.add(profile)
                db.commit()

        # Generate tokens
        access_token = create_token({"sub": str(user.id), "username": user.username})
        refresh_token = create_token({"sub": str(user.id)})

        # Redirect to frontend with token (use the request's origin)
        base_url = str(request.base_url).rstrip('/')
        frontend_url = f"{base_url}/?token={access_token}&user_id={user.id}&username={user.username}&email={user.email}"
        return RedirectResponse(url=frontend_url)

    except Exception as e:
        raise HTTPException(500, f"OAuth error: {str(e)}")


# Include trivia router
try:
    from routers.trivia import router as trivia_router
    app.include_router(trivia_router)
    print("✓ Trivia router loaded")
except ImportError as e:
    print(f"Warning: Could not import trivia router: {e}")

# Include user/friends router
try:
    from routers.user import router as user_router
    app.include_router(user_router)
    print("✓ User router loaded")
except ImportError as e:
    print(f"Warning: Could not import user router: {e}")

# Include admin router
try:
    from routers.admin import router as admin_router
    app.include_router(admin_router)
    print("✓ Admin router loaded")
except ImportError as e:
    print(f"Warning: Could not import admin router: {e}")

# Include Wordle router
try:
    from routers.wordle import router as wordle_router
    app.include_router(wordle_router)
    print("✓ Wordle router loaded")
except Exception as e:
    print(f"⚠ Warning: Could not import wordle router: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

# Include Sports router
try:
    from routers.sports import router as sports_router
    app.include_router(sports_router)
    print("✓ Sports router loaded")
except Exception as e:
    print(f"⚠ Warning: Could not import sports router: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

# Include Reviews router
try:
    from routers.reviews import router as reviews_router
    app.include_router(reviews_router)
    print("✓ Reviews router loaded")
except Exception as e:
    print(f"⚠ Warning: Could not import reviews router: {type(e).__name__}: {e}")

# Include Rankings router
try:
    from routers.rankings import router as rankings_router
    app.include_router(rankings_router)
    print("✓ Rankings router loaded")
except Exception as e:
    print(f"⚠ Warning: Could not import rankings router: {type(e).__name__}: {e}")

# Start odds sync scheduler on startup
@app.on_event("startup")
async def startup_event():
    """Start background services on app startup"""
    try:
        from app.services.odds_sync_scheduler import sync_scheduler
        sync_scheduler.start()
    except Exception as e:
        print(f"⚠ Warning: Could not start odds sync scheduler: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Stop background services on app shutdown"""
    try:
        from app.services.odds_sync_scheduler import sync_scheduler
        sync_scheduler.stop()
    except Exception as e:
        print(f"⚠ Warning: Could not stop odds sync scheduler: {e}")


if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Svidhaus Arena with Google OAuth on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
