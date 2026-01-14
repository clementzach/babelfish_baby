"""
BabelFish Baby - Main application entry point.
"""
from __future__ import annotations
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from typing import Optional
from app.routers import auth, cries, chat
from app.dependencies import get_current_user, get_current_user_optional
from app.models import User
from app.utils.system_checks import check_ffmpeg_installed
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Check system dependencies
ffmpeg_installed, ffmpeg_message = check_ffmpeg_installed()
if not ffmpeg_installed:
    logger.warning("=" * 60)
    logger.warning("MISSING DEPENDENCY: ffmpeg")
    logger.warning("=" * 60)
    logger.warning(ffmpeg_message)
    logger.warning("=" * 60)
    logger.warning("Audio recording features will NOT work until ffmpeg is installed!")
    logger.warning("=" * 60)
else:
    logger.info(f"✓ {ffmpeg_message}")

# Create FastAPI app
app = FastAPI(
    title="BabelFish Baby",
    description="AI-powered baby cry detection and analysis",
    version="1.0.0",
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Include routers
app.include_router(auth.router)
app.include_router(cries.router)
app.include_router(chat.router)


@app.get("/")
async def root(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Root endpoint - redirect to history if logged in, otherwise show login page.
    """
    if current_user:
        return RedirectResponse(url="/history", status_code=302)

    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/history")
async def history_page(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Cry history dashboard page.
    """
    return templates.TemplateResponse(
        "history.html",
        {"request": request, "user": current_user}
    )


@app.get("/record")
async def record_page(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Audio recording interface.
    """
    return templates.TemplateResponse(
        "record.html",
        {"request": request, "user": current_user}
    )


@app.get("/chat/{cry_id}")
async def chat_page(
    cry_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Chat interface for a specific cry.
    """
    return templates.TemplateResponse(
        "chat.html",
        {"request": request, "user": current_user, "cry_id": cry_id}
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
