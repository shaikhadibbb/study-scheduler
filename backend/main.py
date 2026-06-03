import sys
import os
# hack: add backend to path so uvicorn can find app package
# when run from root dir. there is probably a better way.
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routes import router

# Create database tables automatically on startup
# Useful for local setup without needing migrations
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="StudyOpt API",
    description="Study scheduler backend API."
)

# CORS configuration
# Using allow_origins=["*"] for local development so double-clicking HTML pages 
# or running a simple HTTP server on any port (like 8080 or 5500) works smoothly.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

@app.get("/")
def read_root():
    return {
        "status": "healthy",
        "message": "Welcome to StudyOpt API",
        "documentation": "/docs"
    }
