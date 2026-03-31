from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

import config
from data.law_get import maybe_rebuild_law_map
from mcp_server import mcp, mcp_app
from rest_api import api_app, limiter


class ConcurrencyLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.enabled = config.CONCURRENT_LIMIT_ENABLED
        self.total_semaphore = asyncio.Semaphore(max(config.CONCURRENT_LIMIT_TOTAL, 1))

    async def dispatch(self, request: Request, call_next):
        if not self.enabled:
            return await call_next(request)

        await self.total_semaphore.acquire()
        try:
            return await call_next(request)
        finally:
            self.total_semaphore.release()


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with mcp.session_manager.run():
        asyncio.create_task(maybe_rebuild_law_map())
        yield


app = FastAPI(lifespan=lifespan)
app.mount("/api", api_app)
app.mount("/mcp", mcp_app)

if config.RATE_LIMIT_ENABLED:
    app.state.limiter = limiter
    api_app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    api_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    api_app.add_middleware(SlowAPIMiddleware)

app.add_middleware(ConcurrencyLimiterMiddleware)
