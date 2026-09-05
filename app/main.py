from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.router import router as v1_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.core.rate_limit import RateLimitMiddleware

# Configure application logging first
setup_logging()


# ------------------------------------------------------------
# Optional error tracking (Sentry). SENTRY_DSN ထည့်ထားမှသာ activate ဖြစ်သည်
# ------------------------------------------------------------
if settings.SENTRY_DSN:
    import sentry_sdk

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=0.1,
    )

# Production တွင် Swagger/OpenAPI docs များကို ပိတ်ထားပါ (attack surface လျှော့ချရန်)
if settings.is_production:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
else:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        openapi_url="/api/v1/openapi.json",
    )

# FastAPI debug mode ကို settings.DEBUG အတိုင်း သုံးသည် (hardcode မလုပ်ရ)
app.debug = settings.DEBUG

# Register custom AppException handler
register_exception_handlers(app)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        # Debug Toolbar iframe ပေါ်စေရန် Development တွင် SAMEORIGIN ထားပါ
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault(
            "Referrer-Policy", "strict-origin-when-cross-origin"
        )
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        return response


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.RATE_LIMIT_PER_MINUTE)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Debug Toolbar ကို Development တွင်သာ တပ်ဆင်ပါ
if settings.DEBUG:
    from debug_toolbar.middleware import DebugToolbarMiddleware

    app.add_middleware(
        DebugToolbarMiddleware,
        panels=["debug_toolbar.panels.sqlalchemy.SQLAlchemyPanel"],
    )

app.add_middleware(GZipMiddleware, minimum_size=1000)

app.include_router(v1_router)


@app.get("/")
async def root():
    return {"message": "Welcome to Salon Booking API"}


@app.get("/health")
async def health():
    """
    Load balancer / orchestrator အတွက် Health Check Endpoint
    (Rate-limit မှလည်း exempt ထားသည်)
    """
    return JSONResponse(
        status_code=status.HTTP_200_OK, content={"status": "healthy"}
    )