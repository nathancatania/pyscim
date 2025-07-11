import time
import traceback
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import ValidationError
from tortoise.exceptions import IntegrityError, DoesNotExist
from scim.utils import logger
from scim.schemas.error import ErrorResponse
from scim.exceptions import SCIMException


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        try:
            response = await call_next(request)
            return response
            
        except SCIMException as e:
            # Handle SCIM-specific exceptions
            logger.warning(f"SCIM error: {e.detail}")
            return JSONResponse(
                status_code=e.status_code,
                content=e.to_error_response().model_dump(by_alias=True)
            )
            
        except ValidationError as e:
            # Handle Pydantic validation errors
            logger.warning(f"Validation error: {e}")
            error = ErrorResponse(
                status=400,
                detail="Invalid request body",
                scim_type="invalidValue"
            )
            return JSONResponse(
                status_code=400,
                content=error.model_dump(by_alias=True)
            )
            
        except DoesNotExist as e:
            # Handle Tortoise ORM not found errors
            logger.warning(f"Resource not found: {e}")
            error = ErrorResponse(
                status=404,
                detail="Resource not found"
            )
            return JSONResponse(
                status_code=404,
                content=error.model_dump(by_alias=True)
            )
            
        except IntegrityError as e:
            # Handle database integrity errors
            logger.error(f"Database integrity error: {e}")
            
            # Parse the error to provide more specific feedback
            error_str = str(e).lower()
            if "unique" in error_str:
                scim_type = "uniqueness"
                detail = "A resource with the given attribute value already exists"
            else:
                scim_type = None
                detail = "Database constraint violation"
            
            error = ErrorResponse(
                status=409,
                detail=detail,
                scim_type=scim_type
            )
            return JSONResponse(
                status_code=409,
                content=error.model_dump(by_alias=True)
            )
            
        except Exception as e:
            # Handle all other exceptions
            duration = time.time() - start_time
            logger.error(
                f"Unhandled exception in {request.method} {request.url.path} "
                f"(duration: {duration:.3f}s): {e}\n"
                f"{traceback.format_exc()}"
            )
            
            # Don't expose internal errors in production
            if hasattr(request.app.state, "settings") and request.app.state.settings.is_production:
                detail = "An internal error occurred"
            else:
                detail = str(e)
            
            error = ErrorResponse(
                status=500,
                detail=detail
            )
            return JSONResponse(
                status_code=500,
                content=error.model_dump(by_alias=True)
            )