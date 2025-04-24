"""Configuration settings for the Airweave backend.

Wraps environment variables and provides defaults.
"""

import json
import os
from typing import Any, Dict, Optional

from pydantic import PostgresDsn, ValidationInfo, field_validator
from pydantic_settings import BaseSettings

from airweave.core.logging import logger


class Settings(BaseSettings):
    """Pydantic settings class.

    Attributes:
    ----------
        PROJECT_NAME (str): The name of the project.
        LOCAL_DEVELOPMENT (bool): Whether the application is running locally.
        LOCAL_CURSOR_DEVELOPMENT (bool): Whether cursor development features are enabled.
        DTAP_ENVIRONMENT (str): The deployment environment (local, dev, test, prod).
        FRONTEND_LOCAL_DEVELOPMENT_PORT (int): Port for local frontend development.
        FIRST_SUPERUSER (str): The email address of the first superuser.
        FIRST_SUPERUSER_PASSWORD (str): The password of the first superuser.
        ENCRYPTION_KEY (str): The encryption key.
        POSTGRES_HOST (str): The PostgreSQL server hostname.
        POSTGRES_DB (str): The PostgreSQL database name.
        POSTGRES_USER (str): The PostgreSQL username.
        POSTGRES_PASSWORD (str): The PostgreSQL password.
        SQLALCHEMY_ASYNC_DATABASE_URI (Optional[PostgresDsn]): The SQLAlchemy async database URI.
        LOCAL_NGROK_SERVER (Optional[str]): The local ngrok server URL.
        RUN_ALEMBIC_MIGRATIONS (bool): Whether to run the alembic migrations.
        RUN_DB_SYNC (bool): Whether to run the system sync to process sources,
            destinations, and entity types.
        QDRANT_HOST (str): The Qdrant host.
        QDRANT_PORT (int): The Qdrant port.
        QDRANT_URL (str): The Qdrant URL.
        TEXT2VEC_INFERENCE_URL (str): The URL for text2vec-transformers inference service.
        OPENAI_API_KEY (Optional[str]): The OpenAI API key.
        MISTRAL_API_KEY (Optional[str]): The Mistral AI API key.
    """

    PROJECT_NAME: str = "Airweave"
    LOCAL_DEVELOPMENT: bool = False
    LOCAL_CURSOR_DEVELOPMENT: bool = False
    DTAP_ENVIRONMENT: str = "local"
    FRONTEND_LOCAL_DEVELOPMENT_PORT: int = 8080

    FIRST_SUPERUSER: str
    FIRST_SUPERUSER_PASSWORD: str

    AUTH_ENABLED: Optional[bool] = False
    AUTH0_DOMAIN: Optional[str] = None
    AUTH0_AUDIENCE: Optional[str] = None
    AUTH0_RULE_NAMESPACE: Optional[str] = None

    ENCRYPTION_KEY: str

    POSTGRES_HOST: str
    POSTGRES_DB: str = "airweave"
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    SQLALCHEMY_ASYNC_DATABASE_URI: Optional[PostgresDsn] = None

    LOCAL_NGROK_SERVER: Optional[str] = None

    RUN_ALEMBIC_MIGRATIONS: bool = False
    RUN_DB_SYNC: bool = True

    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_URL: str = f"http://{QDRANT_HOST}:{QDRANT_PORT}"

    TEXT2VEC_INFERENCE_URL: str = "http://localhost:9878"

    OPENAI_API_KEY: Optional[str] = None
    MISTRAL_API_KEY: Optional[str] = None

    def __init__(self, **data: Any):
        """Initialize settings and log environment information.

        Args:
            **data: The data to initialize the settings with.
        """
        super().__init__(**data)
        # Log settings on initialization
        self._log_settings()

    def _log_settings(self):
        """Log the settings values for debugging."""
        # Always log basic settings
        logger.info(f"🔧 Environment: {self.DTAP_ENVIRONMENT}")
        logger.info(f"🔧 Project Name: {self.PROJECT_NAME}")
        logger.info(f"🔧 Local Development: {self.LOCAL_DEVELOPMENT}")

        # Log authentication settings
        logger.info(f"🔐 Auth Enabled: {self.AUTH_ENABLED}")
        if self.AUTH_ENABLED:
            logger.info(f"🔐 Auth0 Domain: {self.AUTH0_DOMAIN}")
            logger.info(f"🔐 Auth0 Audience: {self.AUTH0_AUDIENCE}")
            logger.info(f"🔐 Auth0 Rule Namespace: {self.AUTH0_RULE_NAMESPACE}")

        # Log database settings (safely)
        db_uri = str(self.SQLALCHEMY_ASYNC_DATABASE_URI or "")
        safe_db_uri = db_uri
        if db_uri:
            # Mask password in connection string
            if "@" in db_uri and ":" in db_uri:
                parts = db_uri.split("@")
                if len(parts) > 1:
                    credentials = parts[0].split("://")[1] if "://" in parts[0] else parts[0]
                    if ":" in credentials:
                        username = credentials.split(":")[0]
                        safe_db_uri = db_uri.replace(credentials, f"{username}:****")

        logger.info(f"🔧 Database Host: {self.POSTGRES_HOST}")
        logger.info(f"🔧 Database Name: {self.POSTGRES_DB}")
        logger.info(f"🔧 Database URI: {safe_db_uri}")

        # Log flags controlling startup behavior
        logger.info(f"🔧 Run Alembic Migrations: {self.RUN_ALEMBIC_MIGRATIONS}")
        logger.info(f"🔧 Run DB Sync: {self.RUN_DB_SYNC}")

        # Log service URLs
        logger.info(f"🔧 API URL: {self.api_url}")
        logger.info(f"🔧 App URL: {self.app_url}")
        logger.info(f"🔧 Docs URL: {self.docs_url}")
        logger.info(f"🔧 Qdrant URL: {self.QDRANT_URL}")
        logger.info(f"🔧 Text2Vec URL: {self.TEXT2VEC_INFERENCE_URL}")

        # Log model API key availability (not the keys themselves)
        logger.info(f"🔧 OpenAI API Key Present: {bool(self.OPENAI_API_KEY)}")
        logger.info(f"🔧 Mistral API Key Present: {bool(self.MISTRAL_API_KEY)}")

        # Log environment variables in debug mode (sanitized)
        if self.LOCAL_DEVELOPMENT:
            try:
                env_summary = {}
                for key, value in os.environ.items():
                    # Skip CI variables and long values to reduce log size
                    if (
                        key.startswith("CI_")
                        or len(str(value)) > 100
                        or any(
                            pattern in key.lower()
                            for pattern in ["password", "secret", "key", "token"]
                        )
                    ):
                        env_summary[key] = "****"
                    else:
                        env_summary[key] = value

                logger.debug(
                    f"🔧 Environment Variables: {json.dumps(env_summary, indent=2, default=str)}"
                )
            except Exception as e:
                logger.error(f"Failed to log environment variables: {e}")

    @field_validator("AUTH0_DOMAIN", "AUTH0_AUDIENCE", "AUTH0_RULE_NAMESPACE", mode="before")
    def validate_auth0_settings(cls, v: str, info: ValidationInfo) -> str:
        """Validate Auth0 settings when AUTH_ENABLED is True.

        Args:

        ----
            v (str): The value of the Auth0 setting.
            info (ValidationInfo): The validation context containing all field values.

        Returns:
        -------
            str: The validated Auth0 setting.

        Raises:
        ------
            ValueError: If AUTH_ENABLED is True and the Auth0 setting is empty.
        """
        auth_enabled = info.data.get("AUTH_ENABLED", False)
        if auth_enabled and not v:
            field_name = info.field_name
            message = f"{field_name} must be set when AUTH_ENABLED is True"
            logger.error(f"❌ Validation error: {message}")
            raise ValueError(message)
        return v

    @field_validator("SQLALCHEMY_ASYNC_DATABASE_URI", mode="before")
    def assemble_db_connection(cls, v: Optional[str], info: ValidationInfo) -> PostgresDsn:
        """Build the SQLAlchemy database URI.

        Args:
        ----
            v (Optional[str]): The value of the SQLALCHEMY_DATABASE_URI setting.
            info (ValidationInfo): The validation context containing all field values.

        Returns:
        -------
            PostgresDsn: The assembled SQLAlchemy async database URI.

        """
        if isinstance(v, str):
            logger.debug("🔧 Using provided database URI (not showing for security)")
            return v

        # Connect to local PostgreSQL server during local development
        # This allows developers to debug without Docker
        host = info.data.get("POSTGRES_HOST", "localhost")
        logger.debug(f"🔧 Assembling database URI with host: {host}")

        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=info.data.get("POSTGRES_USER"),
            password=info.data.get("POSTGRES_PASSWORD"),
            host=host,
            path=f"{info.data.get('POSTGRES_DB') or ''}",
        )

    @property
    def api_url(self) -> str:
        """The server URL.

        Returns:
            str: The server URL.
        """
        if self.DTAP_ENVIRONMENT == "local":
            return self.LOCAL_NGROK_SERVER or "http://localhost:8001"
        if self.DTAP_ENVIRONMENT == "prod":
            return "https://api.airweave.ai"
        return f"https://api.{self.DTAP_ENVIRONMENT}-airweave.com"

    @property
    def app_url(self) -> str:
        """The app URL.

        Returns:
            str: The app URL.
        """
        if self.DTAP_ENVIRONMENT == "local":
            return f"http://localhost:{self.FRONTEND_LOCAL_DEVELOPMENT_PORT}"
        if self.DTAP_ENVIRONMENT == "prod":
            return "https://app.airweave.ai"
        return f"https://app.{self.DTAP_ENVIRONMENT}-airweave.com"

    @property
    def docs_url(self) -> str:
        """The docs URL.

        Returns:
            str: The docs URL.
        """
        if self.DTAP_ENVIRONMENT == "local":
            return f"http://localhost:{self.FRONTEND_LOCAL_DEVELOPMENT_PORT}"
        if self.DTAP_ENVIRONMENT == "prod":
            return "https://docs.airweave.ai"
        return f"https://docs.{self.DTAP_ENVIRONMENT}-airweave.com"

    def get_debug_info(self) -> Dict[str, Any]:
        """Get debug information for logging.

        Returns:
            Dict[str, Any]: The debug information.
        """
        return {
            "project_name": self.PROJECT_NAME,
            "environment": self.DTAP_ENVIRONMENT,
            "local_development": self.LOCAL_DEVELOPMENT,
            "auth_enabled": self.AUTH_ENABLED,
            "postgres_host": self.POSTGRES_HOST,
            "postgres_db": self.POSTGRES_DB,
            "api_url": self.api_url,
            "app_url": self.app_url,
            "run_migrations": self.RUN_ALEMBIC_MIGRATIONS,
            "run_db_sync": self.RUN_DB_SYNC,
            "hostname": os.environ.get("HOSTNAME", "unknown"),
            "pod_name": os.environ.get("POD_NAME", "unknown"),
            "node_name": os.environ.get("NODE_NAME", "unknown"),
        }


# Initialize settings for the application
settings = Settings()

# Log settings on module import for early debugging
logger.info("🔧 Settings initialized")
logger.info(f"🔧 Debug info: {json.dumps(settings.get_debug_info(), indent=2, default=str)}")
