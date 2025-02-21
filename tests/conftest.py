import pytest
from fastapi.testclient import TestClient
import asyncio
from app.main import app

@pytest.fixture
def test_client():
    return TestClient(app)

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()