from debug_toolbar.middleware import DebugToolbarMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.core.rate_limit import RateLimitMiddleware


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url="/api/v1/openapi.json",
    debug=True, 
)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
         # 2. Debug Toolbar iframe ပေါ်စေရန် Development တွင် SAMEORIGIN ထားပါ
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault(
            "Referrer-Policy", "strict-origin-when-cross-origin"
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
app.add_middleware(
    DebugToolbarMiddleware,
    panels=["debug_toolbar.panels.sqlalchemy.SQLAlchemyPanel"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.include_router(v1_router)

@app.get("/")
async def root():
    return {"message": "Welcome to Salon Booking API"}