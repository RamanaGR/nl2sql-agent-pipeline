"""Pytest fixtures and configuration."""

import os

import pytest
from fastapi.testclient import TestClient


# Ensure test env before any imports that load config
@pytest.fixture(scope="session", autouse=True)
def test_env():
    """Set test environment variables before tests run."""
    os.environ["GEMINI_API_KEY"] = "test-key-for-unit-tests"
    yield
    # Cleanup not strictly needed for session scope


@pytest.fixture
def client():
    """FastAPI test client."""
    from core.config import get_settings
    get_settings.cache_clear()
    from api.main import app
    return TestClient(app)
