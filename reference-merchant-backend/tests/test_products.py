# © 2026 Visa.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Products routes, checked against the data from create_sample_data.py."""

SAMPLE_PRODUCT_COUNT = 20
SAMPLE_CATEGORIES = {"Electronics", "Sports", "Kitchen", "Home", "Books"}


def test_list_products_returns_sample_data(client):
    response = client.get("/api/products/")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == SAMPLE_PRODUCT_COUNT
    assert body["limit"] == 20
    assert body["offset"] == 0
    assert len(body["products"]) == SAMPLE_PRODUCT_COUNT
    first = body["products"][0]
    assert set(first) >= {"id", "name", "description", "price", "category", "image_url", "stock_quantity", "created_at"}


def test_search_by_query_matches_name_or_description(client):
    response = client.get("/api/products/", params={"query": "headphones"})
    names = {p["name"] for p in response.json()["products"]}
    assert names == {"Wireless Headphones"}

    # "noise cancellation" appears only in descriptions.
    response = client.get("/api/products/", params={"query": "noise cancellation"})
    names = {p["name"] for p in response.json()["products"]}
    assert names == {"Wireless Headphones", "Gaming Headset"}


def test_filter_by_category(client):
    response = client.get("/api/products/", params={"category": "Books"})
    body = response.json()
    assert body["total"] == 3
    assert all(p["category"] == "Books" for p in body["products"])


def test_filter_by_price_range(client):
    response = client.get("/api/products/", params={"min_price": 100, "max_price": 300})
    body = response.json()
    prices = [p["price"] for p in body["products"]]
    assert prices and all(100 <= price <= 300 for price in prices)
    assert {p["name"] for p in body["products"]} == {
        "Wireless Headphones", "Running Shoes", "Air Fryer", "Stand Mixer",
    }


def test_pagination(client):
    page1 = client.get("/api/products/", params={"limit": 5, "offset": 0}).json()
    page2 = client.get("/api/products/", params={"limit": 5, "offset": 5}).json()
    assert page1["total"] == page2["total"] == SAMPLE_PRODUCT_COUNT
    assert len(page1["products"]) == len(page2["products"]) == 5
    assert not {p["id"] for p in page1["products"]} & {p["id"] for p in page2["products"]}


def test_invalid_limit_is_rejected(client):
    assert client.get("/api/products/", params={"limit": 0}).status_code == 422
    assert client.get("/api/products/", params={"limit": 101}).status_code == 422


def test_get_categories(client):
    response = client.get("/api/products/categories")
    assert response.status_code == 200
    assert set(response.json()["categories"]) == SAMPLE_CATEGORIES


def test_get_product_by_id(client):
    response = client.get("/api/products/1")
    assert response.status_code == 200
    product = response.json()
    assert product["id"] == 1
    assert product["name"] == "Wireless Headphones"
    assert product["price"] == 199.99


def test_get_unknown_product_returns_404(client):
    response = client.get("/api/products/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"
