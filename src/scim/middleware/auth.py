from datetime import datetime
from typing import Optional, Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from scim.config import settings
from scim.utils import logger
from scim.schemas.error import ErrorResponse
from scim.models import APIToken, Application
from tortoise.exceptions import DoesNotExist
import hashlib


class AuthenticationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, exclude_paths: Optional[list[str]] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            f"{settings.api_prefix}/ServiceProviderConfig",
            f"{settings.api_prefix}/Schemas",
            f"{settings.api_prefix}/ResourceTypes",
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip auth for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Skip if auth is disabled
        if not settings.auth_enabled:
            # Use default tenant and app when auth is disabled
            from scim.services import ApplicationService
            default_app = await ApplicationService.get_or_create_default_application(
                tenant_id="00000000-0000-0000-0000-000000000001"
            )
            request.state.auth_user = {
                "sub": "anonymous", 
                "role": "admin",
                "tenant_id": "00000000-0000-0000-0000-000000000001",  # Default tenant ID
                "app_id": str(default_app.id)
            }
            return await call_next(request)
        
        # Extract token
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return self._unauthorized_response("Missing Authorization header")
        
        try:
            scheme, token = auth_header.split()
            if scheme.lower() != "bearer":
                return self._unauthorized_response("Invalid authentication scheme")
        except ValueError:
            return self._unauthorized_response("Invalid Authorization header format")
        
        # Verify token
        auth_user = await self._verify_token(token)
        if not auth_user:
            return self._unauthorized_response("Invalid or expired token")
        
        # Attach auth info to request
        request.state.auth_user = auth_user
        
        # Process request
        return await call_next(request)
    
    async def _verify_token(self, token: str) -> Optional[dict]:
        try:
            # Check if it's an API token
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            api_token = await APIToken.filter(
                token_hash=token_hash,
                active=True
            ).prefetch_related("app", "app__tenant").first()
            
            if api_token:
                # Check if token is expired
                if api_token.expires_at and api_token.expires_at < datetime.now():
                    logger.warning(f"Expired token used: {api_token.name}")
                    return None
                
                # Update last used timestamp
                api_token.last_used_at = datetime.now()
                await api_token.save()
                
                # Get tenant ID through the application
                app = await api_token.app
                tenant = await app.tenant
                
                return {
                    "sub": f"api_token:{api_token.id}",
                    "role": "api_token",
                    "scopes": api_token.scopes,
                    "token_name": api_token.name,
                    "app_id": str(api_token.app_id),
                    "app_name": app.name,
                    "tenant_id": str(tenant.id),
                }
            
            return None
        
        except DoesNotExist as e:
            logger.error(f"Token verification failed: {e}")
            return None
    
    def _unauthorized_response(self, detail: str) -> JSONResponse:
        error = ErrorResponse(
            status=401,
            detail=detail
        )
        
        return JSONResponse(
            status_code=401,
            content=error.model_dump(by_alias=True),
            headers={"WWW-Authenticate": 'Bearer realm="SCIM API"'}
        )