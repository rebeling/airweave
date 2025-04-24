"""Main module of the FastAPI application.

This module sets up the FastAPI application and the middleware to log incoming requests
and unhandled exceptions.
"""

import os
import subprocess
import time
import traceback
import uuid
from contextlib import asynccontextmanager
from typing import Union

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import ValidationError
from starlette.middleware.cors import CORSMiddleware

from airweave.api.v1.api import api_router
from airweave.core.config import settings
from airweave.core.exceptions import NotFoundException, PermissionException, unpack_validation_error
from airweave.core.logging import logger
from airweave.db.init_db import init_db
from airweave.db.session import AsyncSessionLocal
from airweave.platform.db_sync import sync_platform_components
from airweave.platform.entities._base import ensure_file_entity_models
from airweave.platform.scheduler import platform_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info(f"🚀 Starting application in environment: {settings.DTAP_ENVIRONMENT}")
    logger.info(f"🔧 Running in K8s/container? {not settings.LOCAL_DEVELOPMENT}")
    logger.info(f"🔑 Auth enabled: {settings.AUTH_ENABLED}")
    logger.info(f"📝 CORS origins: {app.state.cors_origins}")

    try:
        async with AsyncSessionLocal() as db:
            if settings.RUN_ALEMBIC_MIGRATIONS:
                logger.info("Running alembic migrations...")
                result = subprocess.run(
                    ["alembic", "upgrade", "head"], check=True, capture_output=True
                )
                logger.info(f"Alembic output: {result.stdout.decode()}")
                logger.info("✅ Alembic migrations complete")
            else:
                logger.info("⏭️ Skipping alembic migrations")

            if settings.RUN_DB_SYNC:
                logger.info("🔄 Starting platform component sync...")
                # Ensure all FileEntity subclasses have their parent and chunk models created
                ensure_file_entity_models()
                await sync_platform_components("airweave/platform", db)
                logger.info("✅ Platform component sync complete")
            else:
                logger.info("⏭️ Skipping platform component sync")

            logger.info("🔄 Initializing database...")
            await init_db(db)
            logger.info("✅ Database initialization complete")

        # Start the sync scheduler
        logger.info("⏰ Starting sync scheduler...")
        await platform_scheduler.start()
        logger.info("✅ Sync scheduler started")

        logger.info("🚀 Application startup complete!")
    except Exception as e:
        logger.error(f"❌ Fatal error during application startup: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

    yield

    # Shutdown
    # Stop the sync scheduler
    logger.info("🛑 Stopping sync scheduler...")
    await platform_scheduler.stop()
    logger.info("✅ Sync scheduler stopped")
    logger.info("👋 Application shutdown complete")


app = FastAPI(title=settings.PROJECT_NAME, openapi_url="/openapi.json", lifespan=lifespan)

# Store CORS origins for logging
app.state.cors_origins = [
    "http://localhost:5173",
    "localhost:8001",
    "http://localhost:8080",
    "https://app.dev-airweave.com",
    "https://app.stg-airweave.com",
    "https://app.airweave.ai",
    "https://docs.airweave.ai",
]

app.include_router(api_router)


@app.middleware("http")
async def add_request_id(request: Request, call_next: callable) -> Response:
    """Middleware to generate and add a request ID to the request for tracing.

    Args:
    ----
        request (Request): The incoming request.
        call_next (callable): The next middleware in the chain.

    Returns:
    -------
        Response: The response to the incoming request.

    """
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    logger.debug(f"🔍 Request ID {request_id} assigned to {request.method} {request.url}")
    return await call_next(request)


@app.middleware("http")
async def log_requests(request: Request, call_next: callable) -> Response:
    """Middleware to log incoming requests.

    Args:
    ----
        request (Request): The incoming request.
        call_next (callable): The next middleware in the chain.

    Returns:
    -------
        Response: The response to the incoming request.

    """
    start_time = time.time()
    client_host = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    auth_header = "present" if request.headers.get("authorization") else "missing"
    content_type = request.headers.get("content-type", "unknown")

    logger.info(f"➡️ Request: {request.method} {request.url.path} from {client_host}")
    logger.debug(f"🔍 Headers: Auth: {auth_header}, Content-Type: {content_type}, UA: {user_agent}")

    try:
        # Log request query params
        if request.query_params:
            logger.debug(f"🔍 Query params: {dict(request.query_params)}")

        # Log request body if available (but don't log passwords or sensitive data)
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    # Only log if small enough, truncate if too large
                    if len(body) < 5000:
                        body_str = body.decode("utf-8")
                        # Don't log if it contains sensitive words
                        if not any(
                            word in body_str.lower()
                            for word in ["password", "secret", "token", "key"]
                        ):
                            logger.debug(f"🔍 Request body: {body_str}")
                        else:
                            logger.debug("🔍 Request body contains sensitive data (not logged)")
                    else:
                        logger.debug("🔍 Request body too large to log")
            except Exception as e:
                logger.warning(f"❌ Failed to log request body: {str(e)}")
    except Exception as e:
        logger.warning(f"❌ Error during request logging: {str(e)}")

    response = await call_next(request)

    duration = time.time() - start_time
    logger.info(
        f"✅ Response: {request.method} {request.url.path} → {response.status_code} in {duration:.4f}s"
    )

    return response


@app.middleware("http")
async def exception_logging_middleware(request: Request, call_next: callable) -> Response:
    """Middleware to log unhandled exceptions.

    Args:
    ----
        request (Request): The incoming request.
        call_next (callable): The next middleware in the chain.

    Returns:
    -------
        Response: The response to the incoming request.

    """
    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        logger.error(f"❌ Unhandled exception on {request.method} {request.url.path}: {exc}")
        if settings.LOCAL_CURSOR_DEVELOPMENT:
            logger.error(f"🔍 Exception traceback: {traceback.format_exc()}")
        else:
            # Log at least the first 5 lines of traceback even in production
            trace_lines = traceback.format_exc().splitlines()
            short_trace = "\n".join(trace_lines[: min(5, len(trace_lines))])
            logger.error(f"🔍 Exception short traceback: {short_trace}")

        logger.error(
            f"🔍 Request details: path={request.url.path}, method={request.method}, client={request.client}"
        )
        return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


@app.exception_handler(RequestValidationError)
@app.exception_handler(ValidationError)
async def validation_exception_handler(
    request: Request, exc: Union[RequestValidationError, ValidationError]
) -> JSONResponse:
    """Exception handler for validation errors that occur during request processing.

    This handler captures exceptions raised due to request data not passing the schema validation.

    It improves the client's ability to understand what part of their request was invalid
    and why, facilitating easier debugging and correction.

    Args:
    ----
        request (Request): The incoming request that triggered the exception.
        exc (Union[RequestValidationError, ValidationError]): The exception object that was raised.
            This can either be a RequestValidationError for request body/schema validation issues,
            or a ValidationError for other data model validations within FastAPI.

    Returns:
    -------
        JSONResponse: A 422 Unprocessable Entity status response that details the validation
            errors. Each error message is a dictionary where the key is the location
            of the validation error in the request, and the value is the associated error message.

    Example of JSON output:
        {
            "errors": [
                {"body.email": "field required"},
                {"body.age": "value is not a valid integer"}
            ],
            "source": "RequestValidationError",
            "request_path": "/api/users",
            "request_method": "POST",
            "schema_info": {
                "name": "UserCreate",
                "module": "airweave.schemas.user",
                "file_path": "/airweave/schemas/user.py"
            },
            "validation_context": [
                "airweave.api.v1.endpoints.users:create_user:42",
                "airweave.schemas.user:UserCreate:15"
            ]
        }

    """
    # Extract basic error messages
    error_messages = unpack_validation_error(exc)

    logger.error(f"❌ Validation error on {request.method} {request.url.path}: {error_messages}")
    logger.error(f"🔍 Full exception details: {exc}")

    if settings.LOCAL_CURSOR_DEVELOPMENT:
        # Additional diagnostic information
        exception_type = exc.__class__.__name__
        exception_str = str(exc)
        class_name = exception_str.split("\n")[0].split(" ")[-1]

        # Extract a simplified stack trace focusing on schema validation
        stack_trace = []
        if hasattr(exc, "__traceback__") and exc.__traceback__ is not None:
            stack_frames = traceback.extract_tb(exc.__traceback__)

            # Create a simplified version for the response
            for frame in stack_frames:
                # Only include frames from our backend code
                if "site-packages" not in frame.filename and "/airweave" in frame.filename:
                    context = f"{frame.filename.split('/')[-1]}:{frame.name}:{frame.lineno}"
                    stack_trace.append(context)

        logger.debug(f"🔍 Validation error stack trace: {stack_trace}")

        return JSONResponse(
            status_code=422,
            content={
                "class_name": class_name,
                "stack_trace": stack_trace,
                "type": exception_type,
                "error_messages": error_messages,
            },
        )

    return JSONResponse(status_code=422, content=error_messages)


@app.exception_handler(PermissionException)
async def permission_exception_handler(request: Request, exc: PermissionException) -> JSONResponse:
    """Exception handler for PermissionException.

    Args:
    ----
        request (Request): The incoming request that triggered the exception.
        exc (PermissionException): The exception object that was raised.

    Returns:
    -------
        JSONResponse: A 403 Forbidden status response that details the error message.

    """
    logger.warning(f"⛔ Permission denied for {request.method} {request.url.path}: {exc}")
    logger.debug(f"🔍 Client IP: {request.client.host if request.client else 'unknown'}")
    logger.debug(
        f"🔍 Auth header present: {'yes' if request.headers.get('authorization') else 'no'}"
    )

    return JSONResponse(status_code=403, content={"detail": str(exc)})


@app.exception_handler(NotFoundException)
async def not_found_exception_handler(request: Request, exc: NotFoundException) -> JSONResponse:
    """Exception handler for NotFoundException.

    Args:
    ----
        request (Request): The incoming request that triggered the exception.
        exc (NotFoundException): The exception object that was raised.

    Returns:
    -------
        JSONResponse: A 404 Not Found status response that details the error message.

    """
    logger.warning(f"🔍 Resource not found for {request.method} {request.url.path}: {exc}")
    return JSONResponse(status_code=404, content={"detail": str(exc)})


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "localhost:8001",
        "http://localhost:8080",
        "https://app.dev-airweave.com",
        "https://app.stg-airweave.com",
        "https://app.airweave.ai",
        "https://docs.airweave.ai",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def show_docs_reference() -> HTMLResponse:
    """Root endpoint to display the API documentation.

    Returns:
    -------
        HTMLResponse: The HTML content to display the API documentation.

    """
    logger.debug("📄 Root endpoint accessed, returning docs reference")
    html_content = """
<!DOCTYPE html>
<html>
    <head>
        <title>Airweave API</title>
    </head>
    <body>
        <h1>Welcome to the Airweave API</h1>
        <p>Please visit the <a href="https://docs.airweave.ai">docs</a> for more information.</p>
    </body>
</html>
    """
    return HTMLResponse(content=html_content)


@app.get("/debug-env", include_in_schema=False)
async def debug_environment() -> JSONResponse:
    """Debug endpoint to view environment variables (sanitized).

    Returns:
    -------
        JSONResponse: A JSON response with environment information.
    """
    if not settings.LOCAL_DEVELOPMENT:
        logger.warning("⛔ Debug endpoint accessed in non-local environment")
        return JSONResponse(
            status_code=403, content={"detail": "Forbidden in non-local environment"}
        )

    env_vars = {}
    sensitive_patterns = ["key", "secret", "password", "token", "auth"]

    # Log environment variables (sanitized) for debugging
    for key, value in os.environ.items():
        # Sanitize sensitive values
        if any(pattern in key.lower() for pattern in sensitive_patterns):
            sanitized_value = "********"
        else:
            sanitized_value = value

        env_vars[key] = sanitized_value

    return JSONResponse(
        content={
            "environment": settings.DTAP_ENVIRONMENT,
            "hostname": os.environ.get("HOSTNAME", "unknown"),
            "pod_name": os.environ.get("POD_NAME", "unknown"),
            "env_vars": env_vars,
            "auth_enabled": settings.AUTH_ENABLED,
        }
    )
