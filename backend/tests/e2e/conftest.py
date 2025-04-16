"""Configuration and fixtures for end-to-end tests."""

import logging
import os
from typing import Dict, Generator

import pytest

from tests.e2e.runner import E2ETestRunner

logger = logging.getLogger(__name__)

# Global runner instance to ensure reuse across test sessions
_runner = None


@pytest.fixture(scope="session")
def test_environment() -> Dict[str, any]:
    """Determine and configure the test environment.

    Returns:
        Dictionary with environment configuration
    """
    # Determine environment from environment variable
    env = os.environ.get("AIRWEAVE_TEST_ENV", "test")

    # Set configuration based on environment
    if env == "test":
        backend_port = 9001  # Test environment port
        frontend_port = None  # No frontend in test environment
    else:  # onboarding environment
        backend_port = 8001  # Onboarding environment port
        frontend_port = 8080  # Frontend port for onboarding

    return {
        "env": env,
        "backend_port": backend_port,
        "frontend_port": frontend_port,
        "backend_url": f"http://localhost:{backend_port}",
        "frontend_url": f"http://localhost:{frontend_port}" if frontend_port else None,
    }


@pytest.fixture(scope="session")
def e2e_environment(test_environment) -> Generator[E2ETestRunner, None, None]:
    """Set up and tear down the E2E test environment.

    This fixture starts all required services using docker-compose
    and tears them down after all tests are complete.

    Only sets up the environment if we're in test mode.
    """
    global _runner

    # Skip setup in onboarding mode - services are already running
    if test_environment["env"] != "test":
        yield None
        return

    # Create runner with minimal mode (postgres and backend only)
    # This avoids issues with Weaviate and Neo4j that can be flaky in tests
    if _runner is None:
        _runner = E2ETestRunner()

    try:
        # Start services (or reuse existing ones)
        logger.info("Starting or reusing E2E test environment")
        _runner.setup()

        # Yield runner for additional operations if needed
        yield _runner
    except Exception as e:
        logger.error(f"Error during E2E environment setup: {e}")
        raise


@pytest.fixture(scope="session")
def e2e_api_url(test_environment) -> str:
    """Return the base URL for API requests in E2E tests."""
    return test_environment["backend_url"] + "/"
