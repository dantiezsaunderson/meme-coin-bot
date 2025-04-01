"""
Health check API endpoint for the Meme Coin Signal Bot.

This module provides a simple health check endpoint for monitoring.
"""
from fastapi import FastAPI, HTTPException
from datetime import datetime
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Meme Coin Signal Bot Health API",
    description="Health check API for the Meme Coin Signal Bot",
    version="1.0.0",
)

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Meme Coin Signal Bot Health API"}

@app.get("/health")
async def health_check():
    """Health check endpoint for Render."""
    try:
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Health check failed")
