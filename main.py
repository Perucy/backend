from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
import requests
import secrets
import hashlib
import base64
import os
from typing import Optional
import json
import uvicorn

from databases.database import engine, Base
from routers.auth_routes import router
from routers.whoop_routes import whoop_router
from routers.spotify_routes import spotify_router

app = FastAPI(
    title="FitPro API", 
    version="1.0.0", 
    description="Fitness tracking app with Spotify and Whoop Integration"
)

# CORS for React Native
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(spotify_router, prefix="/spotify", tags=["spotify"])
app.include_router(whoop_router, prefix="/whoop", tags=["whoop"])
app.include_router(router, prefix="/auth", tags=["Authentication"])

@app.on_event("startup")
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables created/verified")

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "FitPro API is running",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/auth/login, /auth/register, /auth/refresh",
            "whoop": "/whoop/auth/login, /whoop/auth/callback",
            "spotify": "/spotify/auth/login, /spotify/auth/callback",
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    print("🚀 Starting FitPro API...")
    uvicorn.run(app, host="0.0.0.0", port=8000)

