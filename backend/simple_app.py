from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import List

app = FastAPI(
    title="Personalized Learning Co-pilot API",
    description="API for the Personalized Learning Co-pilot POC",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Hello from Learning Co-pilot API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
