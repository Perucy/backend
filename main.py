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

from routers import spotify
from routers import whoop

app = FastAPI(title="FitPro Integration Backend")

# CORS for React Native
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "FitPro Backend is running!", "version": "1.0.0"}

app.include_router(spotify.spotify_router, prefix="/spotify", tags=["spotify"])
app.include_router(whoop.whoop_router, prefix="/whoop", tags=["whoop"])

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

