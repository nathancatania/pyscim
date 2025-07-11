import time
import json
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from scim.utils import logger


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log detailed request and response information"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip logging for health checks and docs
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        start_time = time.time()

        # Log request details
        request_body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                request_body = body.decode("utf-8")

                # Reset body for downstream processing
                async def receive():
                    return {"type": "http.request", "body": body}

                request._receive = receive
            except Exception:
                pass

        # Log incoming request
        logger.info(f"→ {request.method} {request.url.path} " f"from {request.client.host if request.client else 'unknown'}")

        # if request_body and logger.level <= 10:  # DEBUG level
        #     try:
        #         # Try to pretty-print JSON
        #         parsed = json.loads(request_body)
        #         logger.debug(f"Request body:\n{json.dumps(parsed, indent=2)}")
        #     except json.JSONDecodeError:
        #         logger.debug(f"Request body: {request_body}")

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Log response
        logger.info(f"← {response.status_code} {request.method} {request.url.path} " f"({duration:.3f}s)")

        return response
