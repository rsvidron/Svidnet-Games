"""
Full server with authentication
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import auth_simple

app = FastAPI(
    title="SvidNet Arena - Game Platform",
    version="1.0.0",
    description="Multiplayer Game Platform with Authentication"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "🎮 SvidNet Arena - Full Game Platform",
        "version": "1.0.0",
        "features": [
            "User Registration & Login",
            "JWT Authentication",
            "Game Modes",
            "Multiplayer Support"
        ],
        "endpoints": {
            "docs": "/docs",
            "register": "/api/auth/register",
            "login": "/api/auth/login"
        }
    }


# Health check
@app.get("/health")
async def health_check():
    import os
    return {
        "status": "healthy",
        "database": "connected" if os.path.exists("gamedb.db") else "not connected",
        "auth": "enabled"
    }


# Include auth router
app.include_router(auth_simple.router, prefix="/api/auth", tags=["Authentication"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
