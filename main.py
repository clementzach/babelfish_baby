"""
BabelFish Baby - Main application entry point.
"""
from __future__ import annotations
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional
from app.routers import auth, cries, chat
from app.dependencies import get_current_user, get_current_user_optional
from app.models import User
from app.utils.system_checks import check_ffmpeg_installed
from dotenv import load_dotenv
import logging
import os

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
# Get root path for reverse proxy support
root_path = os.getenv("ROOT_PATH", "")

app = FastAPI(
    title="BabelFish Baby",
    description="AI-powered baby cry detection and analysis",
    version="1.0.0",
    root_path=root_path,
    # Explicitly set docs URLs to work with reverse proxy
    docs_url="/docs" if root_path else "/docs",
    openapi_url="/openapi.json" if root_path else "/openapi.json",
)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all incoming requests for debugging."""
    async def dispatch(self, request: Request, call_next):
        logger.info(f"Incoming request: {request.method} {request.url.path} (full: {request.url})")
        logger.info(f"Headers: {dict(request.headers)}")
        response = await call_next(request)
        logger.info(f"Response status: {response.status_code}")
        return response


# Add middleware for debugging
if os.getenv("DEBUG_REQUESTS", "false").lower() == "true":
    app.add_middleware(RequestLoggingMiddleware)
    logger.info("✓ Request logging middleware enabled")


@app.on_event("startup")
async def verify_database_tables():
    """Verify all required database tables exist on startup."""
    from sqlalchemy import inspect
    from app.database import engine

    logger.info("Verifying database tables...")
    logger.info(f"Root path: {app.root_path}")
    logger.info(f"Docs URL: {app.docs_url}")
    logger.info(f"OpenAPI URL: {app.openapi_url}")

    # Expected tables
    required_tables = {
        "users",
        "cry_instances",
        "chat_conversations",
        "cry_embeddings_raw",
        "user_embedding_stats",
    }

    # Get actual tables
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    # Check for missing tables
    missing_tables = required_tables - existing_tables

    if missing_tables:
        error_msg = (
            f"Database initialization error: Missing tables: {', '.join(sorted(missing_tables))}\n"
            f"Please run: python scripts/init_db.py"
        )
        logger.error("=" * 60)
        logger.error("DATABASE ERROR")
        logger.error("=" * 60)
        logger.error(error_msg)
        logger.error("=" * 60)
        raise RuntimeError(error_msg)

    logger.info(f"✓ All {len(required_tables)} required database tables verified")


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
        # Use url_for to generate proper URL with root_path
        history_url = request.url_for('history_page')
        return RedirectResponse(url=str(history_url), status_code=302)

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


@app.get("/debug")
async def debug_info(request: Request):
    """Debug endpoint to check URL generation."""
    from fastapi.responses import HTMLResponse

    static_css = str(request.url_for('static', path='/css/style.css'))
    static_js = str(request.url_for('static', path='/js/notifications.js'))

    html = f"""
    <html>
    <head><title>Debug Info</title></head>
    <body>
        <h1>Debug Information</h1>
        <h2>Request Info:</h2>
        <ul>
            <li>Root path: {request.scope.get('root_path', 'NOT SET')}</li>
            <li>URL: {request.url}</li>
            <li>Base URL: {request.base_url}</li>
        </ul>

        <h2>Headers:</h2>
        <ul>
        {''.join(f'<li>{k}: {v}</li>' for k, v in request.headers.items())}
        </ul>

        <h2>Generated URLs:</h2>
        <ul>
            <li>Static CSS: <a href="{static_css}">{static_css}</a></li>
            <li>Static JS: <a href="{static_js}">{static_js}</a></li>
            <li>History: {request.url_for('history_page')}</li>
            <li>Record: {request.url_for('record_page')}</li>
        </ul>

        <h2>Test CSS Load:</h2>
        <link rel="stylesheet" href="{static_css}">
        <div style="color: red; font-size: 20px;">This should be styled if CSS loads</div>

        <h2>Test JS Load:</h2>
        <script src="{static_js}"></script>
        <script>
        if (typeof showNotification === 'function') {{
            document.write('<p style="color: green;">✓ JavaScript loaded successfully!</p>');
        }} else {{
            document.write('<p style="color: red;">✗ JavaScript failed to load</p>');
        }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


if __name__ == "__main__":
    import uvicorn

    # Only used for local development (python main.py)
    # For production, use: uvicorn main:app --host 127.0.0.1 --port 8001 --proxy-headers
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
