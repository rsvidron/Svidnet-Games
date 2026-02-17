"""
Test API with minimal models - no circular dependencies
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Column, Integer, String, Boolean, Numeric, create_engine
from sqlalchemy.orm import Session, sessionmaker, declarative_base
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
import secrets

# Database setup
DATABASE_URL = "sqlite:///./test_gamedb.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Simple models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="user", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

class UserProfile(Base):
    __tablename__ = "user_profiles"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, nullable=False, index=True)
    elo_rating = Column(Integer, default=1200, nullable=False)
    total_games_played = Column(Integer, default=0, nullable=False)

# Create tables
Base.metadata.create_all(bind=engine)

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "test-secret-key-for-development"
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "message": "🎮 SvidNet Arena - Authentication Test",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health")
def health():
    user_count = SessionLocal().query(User).count()
    return {
        "status": "healthy",
        "database": "connected",
        "total_users": user_count
    }

@app.post("/api/auth/register", response_model=TokenResponse, status_code=201)
def register(data: UserRegister, db: Session = Depends(get_db)):
    """Register new user"""

    # Check username
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(400, "Username already exists")

    # Check email
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(400, "Email already exists")

    # Create user
    user = User(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
        role="user",
        is_active=True
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

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role
        }
    )

@app.post("/api/auth/login", response_model=TokenResponse)
def login(data: UserLogin, db: Session = Depends(get_db)):
    """Login user"""

    # Find user
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(401, "Invalid username or password")

    if not user.is_active:
        raise HTTPException(403, "Account is inactive")

    # Generate tokens
    access_token = create_token({"sub": user.id, "username": user.username})
    refresh_token = create_token({"sub": user.id})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role
        }
    )

@app.get("/api/users/me")
def get_current_user():
    return {"message": "Protected endpoint - requires JWT token"}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting SvidNet Arena Test Server on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
