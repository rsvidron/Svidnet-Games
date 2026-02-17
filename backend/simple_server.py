"""
Simple authentication server - no complex config
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, timedelta
from typing import Optional
import os

# Import our modules
from app.db.session_sqlite import get_db
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token
from app.models.user import User, UserProfile

app = FastAPI(
    title="Svid Net Arena",
    version="1.0.0",
    description="Multiplayer Game Platform"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Schemas
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict

# Routes
@app.get("/")
def root():
    return {
        "message": "🎮 SvidNet Arena API",
        "status": "operational",
        "version": "1.0.0",
        "endpoints": {
            "docs": "/docs",
            "register": "POST /api/auth/register",
            "login": "POST /api/auth/login"
        }
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "database": "connected" if os.path.exists("gamedb.db") else "disconnected"
    }

@app.post("/api/auth/register", response_model=Token, status_code=201)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register new user"""

    # Check existing username
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(400, "Username already exists")

    # Check existing email
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(400, "Email already exists")

    # Create user
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        role="user",
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Create profile
    profile = UserProfile(user_id=new_user.id, elo_rating=1200)
    db.add(profile)
    db.commit()

    # Generate tokens
    access_token = create_access_token(
        data={"sub": new_user.id, "username": new_user.username, "role": new_user.role}
    )
    refresh_token = create_refresh_token(data={"sub": new_user.id})

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        user={
            "id": new_user.id,
            "username": new_user.username,
            "email": new_user.email,
            "role": new_user.role
        }
    )

@app.post("/api/auth/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Login user"""

    # Find user
    user = db.query(User).filter(User.username == credentials.username).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(401, "Invalid credentials")

    if not user.is_active:
        raise HTTPException(403, "Account inactive")

    # Generate tokens
    access_token = create_access_token(
        data={"sub": user.id, "username": user.username, "role": user.role}
    )
    refresh_token = create_refresh_token(data={"sub": user.id})

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        user={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role
        }
    )

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting SvidNet Arena server on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
