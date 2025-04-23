"""Authentication module for the API."""

import logging

from fastapi_auth0 import Auth0
from jose import jwt

from airweave.core.config import settings

auth0 = Auth0(
    domain=settings.AUTH0_DOMAIN,
    api_audience=settings.AUTH0_AUDIENCE,
)


# Add a method to auth0 instance to verify tokens directly
async def get_user_from_token(token: str):
    """Verify a token and return the Auth0User.

    Args:
        token: The JWT token to verify.

    Returns:
        Auth0User if token is valid, None otherwise
    """
    try:
        if not token:
            return None

        # Validate the token using the same logic as in the auth0.get_user method
        unverified_header = jwt.get_unverified_header(token)
        rsa_key = {}

        # Find the correct key
        for key in auth0.jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"],
                }
                break

        if not rsa_key:
            logging.warning("Invalid kid header (wrong tenant or rotated public key)")
            return None

        # Decode and verify the token
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=auth0.algorithms,
            audience=auth0.audience,
            issuer=f"https://{auth0.domain}/",
        )

        # Create an Auth0User from the payload
        return auth0.auth0_user_model(**payload)
    except Exception as e:
        logging.error(f"Error verifying token: {e}")
        return None


# Attach the method to the auth0 instance
auth0.get_user_from_token = get_user_from_token
