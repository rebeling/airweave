"""Authentication module for the API."""

import json
import os
import traceback
from typing import Any, Dict, Optional

from fastapi import Request
from fastapi_auth0 import Auth0, Auth0User
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWKError, JWTError

from airweave.core.config import settings
from airweave.core.logging import logger

# Log detailed auth configuration on startup
logger.info(f"🔐 Initializing auth module with AUTH_ENABLED={settings.AUTH_ENABLED}")

# Initialize Auth0 only if authentication is enabled
if settings.AUTH_ENABLED:
    try:
        logger.info(f"🔐 Configuring Auth0 with domain: {settings.AUTH0_DOMAIN}")
        logger.info(f"🔐 Auth0 audience: {settings.AUTH0_AUDIENCE}")
        auth0 = Auth0(
            domain=settings.AUTH0_DOMAIN,
            api_audience=settings.AUTH0_AUDIENCE,
        )
        logger.info("✅ Auth0 initialization successful")

        # Log additional startup info for debugging
        pod_name = os.environ.get("HOSTNAME", "unknown")
        logger.debug(f"🔍 Auth0 initialized on pod: {pod_name}")
        logger.debug(f"🔍 Auth0 algorithms: {auth0.algorithms}")
        logger.debug(f"🔍 Auth0 rules namespace: {settings.AUTH0_RULE_NAMESPACE}")
    except Exception as e:
        logger.error(f"❌ Auth0 initialization failed: {str(e)}")
        logger.error(f"🔍 Error details: {traceback.format_exc()}")
        raise
else:
    # Create a mock Auth0 instance that doesn't make network calls
    class MockAuth0:
        """A mock Auth0 class that doesn't make network calls for testing/development."""

        def __init__(self):
            """Initialize the mock Auth0 instance."""
            self.domain = "mock-domain.auth0.com"
            self.audience = "https://mock-api/"
            self.algorithms = ["RS256"]
            self.jwks = {"keys": []}
            self.auth0_user_model = Auth0User
            logger.info("🔄 Mock Auth0 instance created with test audience and domain")

        async def get_user(self, creds=None):
            """Always return a mock user in development mode."""
            # For development and testing
            logger.debug(f"🔑 Returning mock user: {settings.FIRST_SUPERUSER}")

            # Log request headers if available
            if hasattr(creds, "headers"):
                auth_header = "present" if "authorization" in creds.headers else "missing"
                logger.debug(f"🔍 Request with auth header: {auth_header}")

            return Auth0User(sub="mock-user-id", email=settings.FIRST_SUPERUSER)

    auth0 = MockAuth0()
    logger.info("ℹ️ Using mock Auth0 instance because AUTH_ENABLED=False")


# Helper to log token info without exposing sensitive data
def _log_token_debug_info(token: str) -> Dict[str, Any]:
    """Extract and return debug info from a token without logging the token itself.

    Args:
        token: The JWT token

    Returns:
        Dictionary with debug information
    """
    if not token:
        return {"token_present": False}

    try:
        # Get unverified header for debugging
        header = jwt.get_unverified_header(token)

        # Get unverified claims (this doesn't validate the token)
        # We just want to see what's in there for debugging
        claims = jwt.get_unverified_claims(token)

        # Extract debugging information without sensitive data
        debug_info = {
            "token_present": True,
            "token_length": len(token),
            "header": {
                "alg": header.get("alg"),
                "typ": header.get("typ"),
                "kid": header.get("kid"),
            },
            "claims": {
                "exp_present": "exp" in claims,
                "iat_present": "iat" in claims,
                "aud_present": "aud" in claims,
                "iss_present": "iss" in claims,
                "sub_present": "sub" in claims,
                "email_present": "email" in claims,
            },
        }

        # Add expiration timestamp for debugging
        if "exp" in claims:
            from datetime import datetime

            exp_time = datetime.fromtimestamp(claims["exp"])
            now = datetime.now()
            debug_info["expiration"] = {
                "timestamp": claims["exp"],
                "readable": exp_time.isoformat(),
                "expired": exp_time < now,
                "seconds_remaining": (
                    (exp_time - now).total_seconds() if exp_time > now else "expired"
                ),
            }

        # Add audience info for debugging audience mismatches
        if "aud" in claims:
            debug_info["audience"] = {
                "token_aud": claims["aud"],
                "expected_aud": settings.AUTH0_AUDIENCE,
                "match": claims["aud"] == settings.AUTH0_AUDIENCE,
            }

        # Add issuer info for debugging
        if "iss" in claims:
            expected_iss = f"https://{auth0.domain}/"
            debug_info["issuer"] = {
                "token_iss": claims["iss"],
                "expected_iss": expected_iss,
                "match": claims["iss"] == expected_iss,
            }

        return debug_info
    except Exception as e:
        return {"token_present": True, "token_length": len(token), "parsing_error": str(e)}


# Add a method to auth0 instance to verify tokens directly
async def get_user_from_token(token: str, request: Optional[Request] = None) -> Optional[Auth0User]:
    """Verify a token and return the Auth0User.

    Args:
        token: The JWT token to verify.
        request: Optional request for additional context in logs

    Returns:
        Auth0User if token is valid, None otherwise
    """
    # Log the verification attempt with context
    client_ip = request.client.host if request and request.client else "unknown"
    request_id = getattr(request.state, "request_id", "unknown") if request else "unknown"
    logger.info(f"🔑 Token verification attempt from {client_ip} (request: {request_id})")

    # If auth is disabled, just return a mock user
    if not settings.AUTH_ENABLED:
        logger.debug("🔍 Auth disabled, returning mock user")
        return Auth0User(sub="mock-user-id", email=settings.FIRST_SUPERUSER)

    try:
        if not token:
            logger.warning("❌ No token provided for verification")
            return None

        # Log token debug info
        debug_info = _log_token_debug_info(token)
        logger.debug(f"🔍 Token debug info: {json.dumps(debug_info, indent=2)}")

        # Validate the token using the same logic as in the auth0.get_user method
        unverified_header = jwt.get_unverified_header(token)
        rsa_key = {}

        # Find the correct key
        key_found = False
        for key in auth0.jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"],
                }
                key_found = True
                break

        if not key_found:
            logger.warning(
                f"❌ Invalid kid header: {unverified_header.get('kid')} (wrong tenant or rotated public key)"
            )
            logger.debug(f"🔍 Available kids: {[k.get('kid') for k in auth0.jwks.get('keys', [])]}")
            return None

        logger.debug(f"✅ Key found with kid: {rsa_key.get('kid')}")

        # Decode and verify the token
        try:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=auth0.algorithms,
                audience=auth0.audience,
                issuer=f"https://{auth0.domain}/",
            )
            logger.debug("✅ Token successfully decoded and verified")

            # Create an Auth0User from the payload
            auth0_user = auth0.auth0_user_model(**payload)
            logger.info(f"✅ Auth successful for user: {auth0_user.email}")
            return auth0_user

        except ExpiredSignatureError:
            logger.warning("❌ Token verification failed: Expired signature")
            return None
        except JWTError as jwt_err:
            logger.warning(f"❌ Token verification failed: {str(jwt_err)}")
            return None

    except JWKError as jwk_err:
        logger.error(f"❌ JWK Error: {str(jwk_err)}")
        return None
    except Exception as e:
        logger.error(f"❌ Token verification error: {str(e)}")
        if settings.LOCAL_DEVELOPMENT:
            logger.error(f"🔍 Error details: {traceback.format_exc()}")
        return None


# Override the original Auth0 get_user method to add logging
original_get_user = auth0.get_user


async def get_user_with_logging(creds):
    """Wrap the original get_user method with logging."""
    logger.info("🔑 Auth0 get_user called")

    # Log headers if available but don't log the actual token
    if hasattr(creds, "headers"):
        headers = dict(creds.headers)
        auth_header_present = "authorization" in headers
        logger.debug(f"🔍 Auth header present: {auth_header_present}")

        if settings.LOCAL_DEVELOPMENT:
            # In local dev, log more headers for debugging
            safe_headers = {
                k: ("present" if k.lower() == "authorization" else v)
                for k, v in headers.items()
                if k.lower() not in ["cookie"]
            }
            logger.debug(f"🔍 Request headers: {json.dumps(safe_headers, indent=2)}")

    try:
        user = await original_get_user(creds)
        if user:
            logger.info(f"✅ Auth successful for user: {user.email}")
        else:
            logger.warning("❌ Auth failed: No user returned")
        return user
    except Exception as e:
        logger.error(f"❌ Auth error in get_user: {str(e)}")
        if settings.LOCAL_DEVELOPMENT:
            logger.error(f"🔍 Auth error details: {traceback.format_exc()}")
        raise


# Replace the original method with our wrapped version
auth0.get_user = get_user_with_logging

# Attach the token verification method to the auth0 instance
auth0.get_user_from_token = get_user_from_token

# Log auth initialization complete
logger.info("✅ Auth module initialization complete")
