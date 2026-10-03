# © 2026 Visa.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""X-Api-Key enforcement across the products, cart and orders routes."""

import pytest

from tests.conftest import TEST_API_KEY

# One representative read-style request per router.
PROTECTED_ENDPOINTS = [
    ("GET", "/api/products/"),
    ("GET", "/api/products/categories"),
    ("GET", "/api/products/1"),
    ("POST", "/api/cart/"),
    ("GET", "/api/orders/?customer_email=nobody@example.com"),
]


@pytest.mark.parametrize("method,url", PROTECTED_ENDPOINTS)
def test_missing_api_key_returns_401(anon_client, method, url):
    response = anon_client.request(method, url)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key."
    assert response.headers["WWW-Authenticate"] == "ApiKey"


@pytest.mark.parametrize("method,url", PROTECTED_ENDPOINTS)
def test_wrong_api_key_returns_401(anon_client, method, url):
    response = anon_client.request(method, url, headers={"X-Api-Key": "wrong-key"})
    assert response.status_code == 401


@pytest.mark.parametrize("method,url", PROTECTED_ENDPOINTS)
def test_valid_api_key_succeeds(anon_client, method, url):
    response = anon_client.request(method, url, headers={"X-Api-Key": TEST_API_KEY})
    assert response.status_code == 200


def test_empty_api_key_returns_401(anon_client):
    response = anon_client.get("/api/products/", headers={"X-Api-Key": ""})
    assert response.status_code == 401


def test_non_ascii_api_key_returns_401_not_500(anon_client):
    response = anon_client.get("/api/products/", headers={"X-Api-Key": "kéy".encode("latin-1")})
    assert response.status_code == 401


def test_unset_server_key_denies_by_default(anon_client, monkeypatch):
    monkeypatch.delenv("MERCHANT_API_KEY")
    response = anon_client.get("/api/products/", headers={"X-Api-Key": TEST_API_KEY})
    assert response.status_code == 500
    assert "MERCHANT_API_KEY" in response.json()["detail"]
