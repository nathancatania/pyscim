from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from tortoise import Tortoise
from scim.config import settings
from scim.middleware import AuthenticationMiddleware, ErrorHandlerMiddleware, RequestLoggingMiddleware
from scim.api.v2.router import router as v2_router
from scim.utils import logger
from scim.schemas import ErrorResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting PyScim application...")
    
    # Initialize Tortoise ORM
    await Tortoise.init(config=settings.tortoise_orm_config)
    await Tortoise.generate_schemas()
    
    logger.info("Database connection established")
    
    yield
    
    # Shutdown
    logger.info("Shutting down PyScim application...")
    await Tortoise.close_connections()
    logger.info("Database connections closed")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="SCIM 2.0 compliant server implementation",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan,
)

# Add middlewares
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(AuthenticationMiddleware)
if settings.debug:
    app.add_middleware(RequestLoggingMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["ETag", "Location"],
)

# Include routers
app.include_router(v2_router)

# Store settings in app state
app.state.settings = settings


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "environment": settings.environment,
        "version": "1.0.0"
    }


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    error = ErrorResponse(
        status=404,
        detail=f"Path {request.url.path} not found"
    )
    return JSONResponse(
        status_code=404,
        content=error.model_dump(by_alias=True)
    )


@app.exception_handler(405)
async def method_not_allowed_handler(request: Request, exc):
    error = ErrorResponse(
        status=405,
        detail=f"Method {request.method} not allowed for path {request.url.path}"
    )
    return JSONResponse(
        status_code=405,
        content=error.model_dump(by_alias=True)
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Log the validation error with details
    logger.error(
        f"Validation error for {request.method} {request.url.path}\n"
        f"Errors: {exc.errors()}\n"
        f"Body: {exc.body if hasattr(exc, 'body') else 'N/A'}"
    )
    
    # Create SCIM-compliant error response
    error = ErrorResponse(
        status=422,
        detail="Invalid request body",
        scim_type="invalidValue"
    )
    
    # In debug mode, include validation details
    if settings.debug:
        error.detail = f"Validation error: {'; '.join([f'{err['loc']}: {err['msg']}' for err in exc.errors()])}"
    
    return JSONResponse(
        status_code=422,
        content=error.model_dump(by_alias=True)
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "scim.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
    )