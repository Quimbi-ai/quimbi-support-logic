"""
AI-First CRM Backend

Philosophy: Intelligence Replaces Interface
- Smart inbox ordering (no sort UI needed)
- AI-generated response drafts (no template selection)
- Proactive context gathering (no manual lookup)
- Auto-categorization (no manual tagging)

Built with FastAPI for high performance async operations.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.config import settings
from app.api import tickets, ai, agents, webhooks
from app.models import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    from app.services.cache import redis_client
    from app.services.quimbi_client import quimbi_client
    import logging

    logger = logging.getLogger(__name__)

    # Track service health
    app.state.db_healthy = False
    app.state.redis_healthy = False
    app.state.quimbi_healthy = False

    # Initialize database with error handling
    logger.info("Initializing database...")
    try:
        await init_db()
        app.state.db_healthy = True
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"⚠️  Database initialization failed: {e}")
        logger.warning("App will start in degraded mode - database operations will fail")

    # Initialize Redis with error handling
    logger.info("Connecting to Redis...")
    try:
        await redis_client.connect()
        app.state.redis_healthy = True
        logger.info("✅ Redis connected successfully")
    except Exception as e:
        logger.error(f"⚠️  Redis connection failed: {e}")
        logger.warning("App will start without Redis caching")

    # Initialize Quimbi client with error handling
    logger.info("Initializing Quimbi client...")
    try:
        await quimbi_client.initialize()
        app.state.quimbi_healthy = True
        logger.info("✅ Quimbi client initialized successfully")
    except Exception as e:
        logger.error(f"⚠️  Quimbi client initialization failed: {e}")
        logger.warning("App will start without Quimbi intelligence features")

    if app.state.db_healthy and app.state.redis_healthy and app.state.quimbi_healthy:
        logger.info("✅ All services initialized successfully!")
    else:
        logger.warning(f"⚠️  App started in degraded mode - DB: {app.state.db_healthy}, Redis: {app.state.redis_healthy}, Quimbi: {app.state.quimbi_healthy}")

    yield

    # Shutdown
    logger.info("Shutting down services...")
    try:
        await redis_client.close()
    except Exception as e:
        logger.error(f"Error closing Redis: {e}")
    try:
        await quimbi_client.close()
    except Exception as e:
        logger.error(f"Error closing Quimbi client: {e}")
    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="AI-First CRM",
    description="Intelligent customer support system with invisible AI",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware (restricted for security)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],  # Explicit methods only
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "Accept"],  # Specific headers only
    max_age=600  # Cache preflight requests for 10 minutes
)

# Rate limiting exception handler
app.state.limiter = webhooks.limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include routers
app.include_router(tickets.router, prefix="/api", tags=["tickets"])
app.include_router(ai.router, prefix="/api/ai", tags=["ai"])
app.include_router(agents.router)
app.include_router(webhooks.router)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "AI-First CRM",
        "philosophy": "Intelligence Replaces Interface",
        "version": "1.0.0"
    }


@app.get("/health")
async def health(request: Request):
    """Detailed health check."""
    # Get service health from app state
    db_healthy = getattr(request.app.state, 'db_healthy', False)
    redis_healthy = getattr(request.app.state, 'redis_healthy', False)
    quimbi_healthy = getattr(request.app.state, 'quimbi_healthy', False)

    # Overall status
    all_healthy = db_healthy and redis_healthy and quimbi_healthy
    status = "healthy" if all_healthy else "degraded"

    return {
        "status": status,
        "environment": settings.environment,
        "services": {
            "database": "connected" if db_healthy else "disconnected",
            "redis_cache": "connected" if redis_healthy else "unavailable",
            "quimbi_api": "connected" if quimbi_healthy else "unavailable"
        },
        "features": {
            "smart_inbox_ordering": True,
            "topic_alerts": True,
            "ai_draft_generation": quimbi_healthy,
            "ai_recommendations": quimbi_healthy,
            "customer_intelligence": quimbi_healthy,
            "caching": redis_healthy,
            "gorgias_webhook": True,
            "shopify_fulfillment_tracking": True,
            "split_shipment_detection": True
        },
        "quimbi_base_url": settings.quimbi_base_url
    }
