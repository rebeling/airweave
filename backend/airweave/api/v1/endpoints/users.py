"""The API module that contains the endpoints for users.

Important: this module is co-responsible with the CRUD layer for secure transactions with the
database, as it contains the endpoints for user creation and retrieval.
"""

import json
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi_auth0 import Auth0User
from sqlalchemy.ext.asyncio import AsyncSession

from airweave import crud, schemas
from airweave.api import deps
from airweave.api.auth import auth0
from airweave.core.config import settings
from airweave.core.logging import logger
from airweave.schemas import User

router = APIRouter()


@router.get("/", response_model=User)
async def read_user(
    *,
    request: Request,
    current_user: User = Depends(deps.get_user),
) -> schemas.User:
    """Get current user.

    Args:
    ----
        request (Request): The current request.
        current_user (User): The current user.

    Returns:
    -------
        schemas.User: The user object.

    """
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"👤 User data requested: {current_user.email} from IP {client_ip}")
    logger.debug(
        f"🔍 User details: ID={current_user.id}, has_org={bool(current_user.organization_id)}"
    )

    # Log headers for debugging auth issues
    if settings.LOCAL_DEVELOPMENT:
        auth_header = "present" if request.headers.get("authorization") else "missing"
        log_headers = {
            "authorization": auth_header,
            "user-agent": request.headers.get("user-agent", "unknown"),
            "x-forwarded-for": request.headers.get("x-forwarded-for", "unknown"),
            "host": request.headers.get("host", "unknown"),
        }
        logger.debug(f"🔍 Request headers: {json.dumps(log_headers)}")

    return current_user


@router.post("/create_or_update", response_model=User)
async def create_or_update_user(
    request: Request,
    user_data: schemas.UserCreate,
    db: AsyncSession = Depends(deps.get_db),
    auth0_user: Optional[Auth0User] = Depends(auth0.get_user),
) -> schemas.User:
    """Create new user in database if it does not exist.

    Can only create user with the same email as the authenticated user.

    Args:
        request (Request): The request object
        user_data (schemas.UserCreate): The user object to be created.
        db (AsyncSession): Database session dependency to handle database operations.
        auth0_user (Auth0User): Authenticated auth0 user.

    Returns:
        schemas.User: The created user object.

    Raises:
        HTTPException: If the user is not authorized to create this user.
    """
    client_ip = request.client.host if request.client else "unknown"
    request_id = getattr(request.state, "request_id", "unknown")

    logger.info(f"👤 User create/update request: {user_data.email} from IP {client_ip}")
    logger.info(f"🔑 Auth0 user email: {auth0_user.email if auth0_user else 'None'}")

    # Check environment variables for debugging
    if settings.LOCAL_DEVELOPMENT:
        logger.debug(f"🔍 AUTH_ENABLED: {settings.AUTH_ENABLED}")
        logger.debug(f"🔍 AUTH0_DOMAIN: {settings.AUTH0_DOMAIN}")
        logger.debug(f"🔍 AUTH0_AUDIENCE: {settings.AUTH0_AUDIENCE}")

    # Log detailed request info
    if settings.LOCAL_DEVELOPMENT or settings.DTAP_ENVIRONMENT != "prod":
        auth_header = "present" if request.headers.get("authorization") else "missing"
        log_data = {
            "request_id": request_id,
            "auth_header": auth_header,
            "email_match": user_data.email == (auth0_user.email if auth0_user else None),
            "auth0_user_present": auth0_user is not None,
            "pod_name": os.environ.get("HOSTNAME", "unknown"),
        }
        logger.debug(f"🔍 Create/update request details: {json.dumps(log_data)}")

    # Email validation
    if not auth0_user:
        logger.error(f"❌ No Auth0 user found for {user_data.email} from {client_ip}")
        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
        )

    if user_data.email != auth0_user.email:
        logger.error(
            f"❌ Email mismatch: {user_data.email} (request) vs {auth0_user.email} (auth0) from {client_ip}"
        )
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to create this user.",
        )

    # Get existing user
    user = await crud.user.get_by_email(db, email=user_data.email)
    if user:
        logger.info(f"✅ Found existing user for {user_data.email}, returning")
        logger.debug(f"🔍 Existing user: ID={user.id}, org={user.organization_id}")
        return user

    # Create new user
    logger.info(f"➕ Creating new user for {user_data.email}")
    try:
        user = await crud.user.create(db, obj_in=user_data)
        logger.info(f"✅ User created successfully: {user.email} (ID: {user.id})")
        return user
    except Exception as e:
        logger.error(f"❌ Failed to create user {user_data.email}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create user: {str(e)}",
        )
