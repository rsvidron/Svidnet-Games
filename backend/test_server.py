"""
Minimal test server to verify FastAPI is working
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(
    title="SvidNet Arena - Test Server",
    version="1.0.0",
    description="Testing basic FastAPI functionality"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "🎮 SvidNet Arena is running!",
        "status": "operational",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "database": "connected" if os.path.exists("gamedb.db") else "not initialized"
    }

@app.get("/test/hello/{name}")
async def hello(name: str):
    return {
        "message": f"Hello, {name}! Welcome to SvidNet Arena 🎮"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
