"""
Enhanced API with Google OAuth support
"""
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import Column, Integer, String, Boolean, create_engine
from sqlalchemy.orm import Session, sessionmaker, declarative_base
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from authlib.integrations.starlette_client import OAuth
import os
import httpx

# Database setup
DATABASE_URL = "sqlite:///./oauth_gamedb.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)  # Nullable for OAuth users
    google_id = Column(String(255), unique=True, nullable=True, index=True)
    avatar_url = Column(String(500), nullable=True)
    role = Column(String(20), default="user", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    auth_provider = Column(String(20), default="local", nullable=False)  # local, google

class UserProfile(Base):
    __tablename__ = "user_profiles"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, nullable=False, index=True)
    elo_rating = Column(Integer, default=1200, nullable=False)
    total_games_played = Column(Integer, default=0, nullable=False)

# Import trivia models so they register with the Base
try:
    from models.trivia import TriviaGame, TriviaAnswer, TriviaLeaderboard
except ImportError:
    pass  # Trivia models not yet available

# Create all tables (including trivia tables if imported)
Base.metadata.create_all(bind=engine)

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
    expire = datetime.utcnow() + timedelta(hours=24)
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
app = FastAPI(title="SvidNet Arena", version="1.0.0")

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
    """Serve the frontend HTML"""
    frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "oauth-index.html")
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    # Fallback to API response if frontend not found
    oauth_enabled = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)
    return {
        "message": "🎮 SvidNet Arena - With Google OAuth",
        "version": "1.0.0",
        "status": "running",
        "features": {
            "standard_auth": True,
            "google_oauth": oauth_enabled
        },
        "docs": "/docs",
        "frontend": "not found - check deployment"
    }

@app.get("/trivia")
def trivia_game():
    """Serve the trivia game HTML"""
    trivia_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "trivia-game.html")
    if os.path.exists(trivia_path):
        return FileResponse(trivia_path)
    raise HTTPException(404, "Trivia game not found")

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

    access_token = create_token({"sub": user.id, "username": user.username})
    refresh_token = create_token({"sub": user.id})

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
    if not user or not user.hashed_password or not verify_password(data.password, user.hashed_password):
        raise HTTPException(401, "Invalid username or password")

    if not user.is_active:
        raise HTTPException(403, "Account is inactive")

    access_token = create_token({"sub": user.id, "username": user.username})
    refresh_token = create_token({"sub": user.id})

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
        access_token = create_token({"sub": user.id, "username": user.username})
        refresh_token = create_token({"sub": user.id})

        # Redirect to frontend with token
        frontend_url = f"http://localhost:3000/?token={access_token}&user_id={user.id}&username={user.username}&email={user.email}"
        return RedirectResponse(url=frontend_url)

    except Exception as e:
        raise HTTPException(500, f"OAuth error: {str(e)}")


# Include trivia router
try:
    from routers.trivia import router as trivia_router
    app.include_router(trivia_router)
except ImportError as e:
    print(f"Warning: Could not import trivia router: {e}")


if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting SvidNet Arena with Google OAuth on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
