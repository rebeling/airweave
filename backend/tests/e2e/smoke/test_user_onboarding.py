"""User onboarding test with Stripe source connection.

Tests the end-to-end flow a new user would experience:
1. Connect to Stripe data source
2. Create a sync
3. Run the sync job
4. Test search functionality
"""

import os
import time
import uuid

import pytest
import requests

from airweave.core.constants.native_connections import NATIVE_TEXT2VEC_UUID


@pytest.fixture
def source_connection_data():
    """Fixture to provide test source connection data."""
    # Include both connection name and credential information in config_fields
    stripe_api_key = os.getenv("STRIPE_API_KEY")
    return {
        "name": "Test Source Connection",
        "config_fields": {
            # Add required configuration fields for Stripe (StripeAuthConfig)
            "api_key": stripe_api_key,
        },
    }


@pytest.fixture
def sync_data():
    """Fixture to provide test sync data."""
    return {
        "name": f"Test Sync {uuid.uuid4()}",
        "description": "Test sync created by E2E test",
        "source_connection_id": None,  # Will be created during test
        "destination_connection_ids": [],  # Will be populated during test
        "embedding_model_connection_id": str(
            NATIVE_TEXT2VEC_UUID
        ),  # Use the default native embedding model
        "run_immediately": False,
        "schedule": None,
    }


def test_user_onboarding(e2e_api_url, source_connection_data, sync_data):
    """Test the end-to-end user onboarding flow with Stripe integration.

    Tests creating a connection to Stripe, setting up a sync job,
    running the sync, and verifying search functionality.
    """
    # Step 1: Create a source connection
    create_connection_response = requests.post(
        f"{e2e_api_url}/connections/connect/source/stripe", json=source_connection_data
    )
    assert create_connection_response.status_code == 200, (
        f"Failed to create connection: {create_connection_response.text}"
    )

    # Update the sync data with the source connection ID
    sync_data["source_connection_id"] = create_connection_response.json()["id"]

    # Step 2: Create a new sync
    create_sync_response = requests.post(f"{e2e_api_url}/sync/", json=sync_data)
    assert create_sync_response.status_code == 200, (
        f"Failed to create sync: {create_sync_response.text}"
    )

    # Save the sync_id
    sync = create_sync_response.json()
    sync_id = sync["id"]

    # Step 3: Run a sync job
    run_sync_response = requests.post(f"{e2e_api_url}/sync/{sync_id}/run")
    assert run_sync_response.status_code == 200, f"Failed to run sync: {run_sync_response.text}"
    sync_job = run_sync_response.json()
    job_id = sync_job["id"]

    # Wait for the job to complete if it's not already done
    if sync_job["status"] not in ["completed"]:
        # Poll job status with timeout
        max_wait_time = 300  # seconds
        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            job_status_response = requests.get(
                f"{e2e_api_url}/sync/{sync_id}/job/{job_id}", params={"sync_id": sync_id}
            )
            assert job_status_response.status_code == 200, (
                f"Failed to get job status: {job_status_response.text}"
            )

            current_status = job_status_response.json()["status"]
            if current_status == "completed":
                break
            elif current_status == "failed":
                raise AssertionError(f"Sync job failed: {job_status_response.json()}")

            time.sleep(10)  # Wait before polling again

        # Verify the job completed within the timeout
        assert time.time() - start_time < max_wait_time, "Sync job did not complete within timeout"
        assert current_status == "completed", f"Unexpected job status: {current_status}"

    # Step 4: Test search functionality
    # First, define a search query relevant to Stripe data
    search_query = "What did Daan Manneke buy according to the invoice?"

    # Perform the search
    search_response = requests.get(
        f"{e2e_api_url}/search/", params={"sync_id": sync_id, "query": search_query}
    )
    print(f"\n{search_response}\n")
    assert search_response.status_code == 200, f"Search failed: {search_response.text}"

    # Verify search results
    search_results = search_response.json()
    assert isinstance(search_results, list), "Search results should be a list"

    # If the Stripe data contains the search term, we should get results
    # Note: This might need adjustment based on the test data available
    if search_results:
        # Verify the structure of search results
        for result in search_results:
            # Verify each result has expected fields
            assert "metadata" in result, "Result should have metadata"
            assert "text" in result, "Result should have text content"
            assert "score" in result, "Result should have a relevance score"
