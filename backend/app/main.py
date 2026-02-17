"""
Main FastAPI application
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from .core.config import settings
from .core.redis import redis_client
from .api.endpoints import auth, users, trivia, games, wordle, sports, leaderboards, friends, admin
from .api.websockets import game_rooms

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("Starting application...")
    await redis_client.connect()
    logger.info("Connected to Redis")
    yield
    # Shutdown
    logger.info("Shutting down application...")
    await redis_client.disconnect()
    logger.info("Disconnected from Redis")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Multiplayer Game Platform API",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }


# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(trivia.router, prefix="/api/trivia", tags=["Trivia"])
app.include_router(games.router, prefix="/api/games", tags=["Games"])
app.include_router(wordle.router, prefix="/api/wordle", tags=["Wordle"])
app.include_router(sports.router, prefix="/api/sports", tags=["Sports"])
app.include_router(leaderboards.router, prefix="/api/leaderboards", tags=["Leaderboards"])
app.include_router(friends.router, prefix="/api/friends", tags=["Friends"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])

# WebSocket endpoint
app.include_router(game_rooms.router, prefix="/ws", tags=["WebSocket"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
