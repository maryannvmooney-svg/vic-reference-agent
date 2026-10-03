# © 2026 Visa.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Orders routes, using orders placed through cart checkout."""

import uuid


def test_list_orders_requires_customer_email(client):
    response = client.get("/api/orders/")
    assert response.status_code == 400
    assert response.json()["detail"] == "customer_email is required."


def test_list_orders_for_customer(client, placed_order):
    order, email = placed_order
    response = client.get("/api/orders/", params={"customer_email": email})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    listed = body["orders"][0]
    assert listed["id"] == order["id"]
    assert listed["order_number"] == order["order_number"]
    assert listed["items"][0]["product"]["name"] == "Wireless Headphones"


def test_list_orders_filters_by_status(client, placed_order):
    _, email = placed_order
    confirmed = client.get("/api/orders/", params={"customer_email": email, "status": "confirmed"}).json()
    shipped = client.get("/api/orders/", params={"customer_email": email, "status": "shipped"}).json()
    assert confirmed["total"] == 1
    assert shipped["total"] == 0


def test_list_orders_for_other_customer_is_empty(client, placed_order):
    response = client.get("/api/orders/", params={"customer_email": "someone-else@example.com"})
    assert response.status_code == 200
    assert response.json() == {"orders": [], "total": 0}


def test_get_order_by_id(client, placed_order):
    order, email = placed_order
    response = client.get(f"/api/orders/{order['id']}", params={"customer_email": email})
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == order["id"]
    assert body["status"] == "confirmed"


def test_get_order_by_id_email_is_case_insensitive(client, placed_order):
    order, email = placed_order
    response = client.get(f"/api/orders/{order['id']}", params={"customer_email": email.upper()})
    assert response.status_code == 200


def test_get_order_with_wrong_email_returns_404(client, placed_order):
    order, _ = placed_order
    response = client.get(f"/api/orders/{order['id']}", params={"customer_email": "attacker@example.com"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Order not found"


def test_get_unknown_order_returns_404(client):
    response = client.get(f"/api/orders/{uuid.uuid4()}", params={"customer_email": "a@example.com"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Order not found"


def test_get_order_requires_customer_email(client, placed_order):
    order, _ = placed_order
    assert client.get(f"/api/orders/{order['id']}").status_code == 422


def test_get_order_by_number(client, placed_order):
    order, email = placed_order
    response = client.get(f"/api/orders/number/{order['order_number']}", params={"customer_email": email})
    assert response.status_code == 200
    assert response.json()["id"] == order["id"]


def test_get_order_by_number_with_wrong_email_returns_404(client, placed_order):
    order, _ = placed_order
    response = client.get(
        f"/api/orders/number/{order['order_number']}", params={"customer_email": "attacker@example.com"}
    )
    assert response.status_code == 404


def test_update_order_status(client, placed_order):
    order, email = placed_order
    response = client.put(f"/api/orders/{order['id']}/status", params={"status": "shipped", "customer_email": email})
    assert response.status_code == 200
    assert response.json()["status"] == "shipped"
    fetched = client.get(f"/api/orders/{order['id']}", params={"customer_email": email}).json()
    assert fetched["status"] == "shipped"


def test_update_order_status_rejects_invalid_status(client, placed_order):
    order, email = placed_order
    response = client.put(f"/api/orders/{order['id']}/status", params={"status": "lost", "customer_email": email})
    assert response.status_code == 400
    assert "Invalid status" in response.json()["detail"]


def test_update_order_status_with_wrong_email_returns_404(client, placed_order):
    order, email = placed_order
    response = client.put(
        f"/api/orders/{order['id']}/status", params={"status": "cancelled", "customer_email": "attacker@example.com"}
    )
    assert response.status_code == 404
    # The order is unchanged.
    fetched = client.get(f"/api/orders/{order['id']}", params={"customer_email": email}).json()
    assert fetched["status"] == "confirmed"


def test_cancel_order(client, placed_order):
    order, email = placed_order
    response = client.delete(f"/api/orders/{order['id']}", params={"customer_email": email})
    assert response.status_code == 200
    assert response.json()["message"] == f"Order {order['order_number']} has been cancelled successfully"
    fetched = client.get(f"/api/orders/{order['id']}", params={"customer_email": email}).json()
    assert fetched["status"] == "cancelled"


def test_cannot_cancel_shipped_order(client, placed_order):
    order, email = placed_order
    client.put(f"/api/orders/{order['id']}/status", params={"status": "shipped", "customer_email": email})
    response = client.delete(f"/api/orders/{order['id']}", params={"customer_email": email})
    assert response.status_code == 400
    assert "cannot be cancelled" in response.json()["detail"]


def test_cancel_order_with_wrong_email_returns_404(client, placed_order):
    order, _ = placed_order
    response = client.delete(f"/api/orders/{order['id']}", params={"customer_email": "attacker@example.com"})
    assert response.status_code == 404
