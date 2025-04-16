"""Health check tests for Airweave.

These tests verify critical components are working in both:
- Test environment: Run by GitHub Actions during backend tests.yml
- Onboarding environment: Run after start.sh execution in onboarding-test.yml
"""

import requests


def test_backend_health(test_environment):
    """Test that the backend API is healthy and responding."""
    health_url = f"{test_environment['backend_url']}/health"

    response = requests.get(health_url, timeout=10)

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "healthy"


def test_documentation_availability(test_environment):
    """Test that documentation is accessible for users."""
    # Test API docs
    api_docs_url = f"{test_environment['backend_url']}/docs"
    response = requests.get(api_docs_url, timeout=10)
    assert response.status_code == 200
    assert "swagger-ui" in response.text.lower()
