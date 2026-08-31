import time
from collections import defaultdict, deque
from typing import Deque, Dict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from app.core.config import settings
from app.core.redis_client import get_redis_client


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, requests_per_minute: int):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self._fallback_hits: Dict[str, Deque[float]] = defaultdict(deque)

    def _client_ip(self, request: Request) -> str:
        """
        Trusted reverse-proxy / load balancer နောက်တွင်ရှိပါက real client IP ကို
        X-Forwarded-For မှယူသည်။ TRUST_PROXY_HEADERS=False ဆိုလျှင် header ကို
        မယုံပဲ socket IP ကိုသာသုံးသည် (header spoofing ကာကွယ်ရန်)။
        """
        if settings.TRUST_PROXY_HEADERS:
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                # Client IP သည် comma-separated list ၏ ပထမဆုံး entry ဖြစ်သည်
                return forwarded.split(",")[0].strip()

        return request.client.host if request.client else "unknown"

    async def dispatch(self, request, call_next):
        if request.url.path in ("/health", "/api/v1/health"):
            return await call_next(request)

        client = self._client_ip(request)
        key = f"rate-limit:{client}"

        allowed = await self._allow_request(key)
        if not allowed:
            return JSONResponse(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": "60"},
            )

        return await call_next(request)

    async def _allow_request(self, key: str) -> bool:
        try:
            redis = get_redis_client()
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, 60)
            return count <= self.requests_per_minute
        except Exception:
            return self._allow_request_in_memory(key)

    def _allow_request_in_memory(self, key: str) -> bool:
        now = time.monotonic()
        window_start = now - 60
        hits = self._fallback_hits[key]

        while hits and hits[0] < window_start:
            hits.popleft()

        if len(hits) >= self.requests_per_minute:
            return False

        hits.append(now)
        return True
