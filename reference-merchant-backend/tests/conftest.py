# © 2026 Visa.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Shared pytest fixtures for the reference merchant backend.

The suite runs against a throwaway SQLite database seeded by
`create_sample_data.py`, with `MERCHANT_API_KEY` set to a test-only value.
"""

import asyncio
import os
import uuid
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

TEST_API_KEY = "test-merchant-api-key"

# Must be set before the app is imported/started; auth reads it per request.
os.environ["MERCHANT_API_KEY"] = TEST_API_KEY

# Standard Visa test card number (passes the Luhn check); not a real card.
TEST_CARD_NUMBER = "4111111111111111"


@pytest.fixture(scope="session", autouse=True)
def sample_database(tmp_path_factory):
    """Seed a fresh database in a temp dir using the sample data script.

    The app uses the relative path ./data/merchant.db, so the tests run from
    an isolated working directory and never touch a developer's local data.
    """
    workdir = tmp_path_factory.mktemp("merchant")
    original_cwd = os.getcwd()
    os.chdir(workdir)

    import create_sample_data
    from app.database import database

    async def seed():
        await create_sample_data.main()
        await database.engine.dispose()

    asyncio.run(seed())
    # Let the app build a fresh engine on its own event loop at startup.
    database.engine = None
    database.AsyncSessionLocal = None

    yield workdir

    os.chdir(original_cwd)


class ApiKeyClient:
    """Wraps a TestClient so every request carries the given X-Api-Key."""

    def __init__(self, client, api_key):
        self._client = client
        self._api_key = api_key

    def request(self, method, url, headers=None, **kwargs):
        merged = {"X-Api-Key": self._api_key, **(headers or {})}
        return self._client.request(method, url, headers=merged, **kwargs)

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self.request("POST", url, **kwargs)

    def put(self, url, **kwargs):
        return self.request("PUT", url, **kwargs)

    def delete(self, url, **kwargs):
        return self.request("DELETE", url, **kwargs)


@pytest.fixture(scope="session")
def anon_client(sample_database):
    """Client that sends no X-Api-Key header."""
    from app.main import app

    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="session")
def client(anon_client):
    """Client that sends the valid X-Api-Key header on every request."""
    return ApiKeyClient(anon_client, TEST_API_KEY)


@pytest.fixture
def cart(client):
    """A new, empty cart."""
    response = client.post("/api/cart/")
    assert response.status_code == 200
    return response.json()


@pytest.fixture
def checkout_payload():
    """Valid checkout data with a unique customer email per test."""
    return {
        "customer_email": f"test-{uuid.uuid4().hex[:8]}@example.com",
        "customer_name": "Test Customer",
        "card_number": TEST_CARD_NUMBER,
        "expiry_date": f"12/{(datetime.now().year + 2) % 100:02d}",
        "cvv": "123",
        "name_on_card": "Test Customer",
        "shipping_address": {
            "street": "1 Test Street",
            "city": "Testville",
            "state": "CA",
            "zip": "94000",
            "country": "US",
        },
    }


@pytest.fixture
def placed_order(client, cart, checkout_payload):
    """Check out a cart containing two units of product 1; returns (order, email)."""
    session_id = cart["session_id"]
    response = client.post(f"/api/cart/{session_id}/items", json={"product_id": 1, "quantity": 2})
    assert response.status_code == 200
    response = client.post(f"/api/cart/{session_id}/checkout", json=checkout_payload)
    assert response.status_code == 200, response.text
    return response.json()["order"], checkout_payload["customer_email"]
