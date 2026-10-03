# © 2026 Visa.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Cart routes, including checkout."""

import uuid

import pytest

# Sample-data prices: product 1 = Wireless Headphones, product 4 = Coffee Maker.
HEADPHONES_ID, HEADPHONES_PRICE = 1, 199.99
COFFEE_MAKER_ID, COFFEE_MAKER_PRICE = 4, 89.99


def add_item(client, session_id, product_id, quantity):
    return client.post(f"/api/cart/{session_id}/items", json={"product_id": product_id, "quantity": quantity})


def test_create_cart(client):
    response = client.post("/api/cart/")
    assert response.status_code == 200
    body = response.json()
    uuid.UUID(body["session_id"])
    assert body["items"] == []
    assert body["total_amount"] == 0.0


def test_get_cart(client, cart):
    response = client.get(f"/api/cart/{cart['session_id']}")
    assert response.status_code == 200
    assert response.json()["session_id"] == cart["session_id"]


def test_get_unknown_cart_returns_404(client):
    response = client.get(f"/api/cart/{uuid.uuid4()}")
    assert response.status_code == 404


def test_add_item_and_totals(client, cart):
    response = add_item(client, cart["session_id"], HEADPHONES_ID, 2)
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["product"]["name"] == "Wireless Headphones"
    assert body["items"][0]["quantity"] == 2

    subtotal = HEADPHONES_PRICE * 2
    tax = round(subtotal * 0.08, 2)
    assert body["subtotal"] == pytest.approx(subtotal)
    assert body["tax"] == pytest.approx(tax)
    assert body["shipping"] == pytest.approx(9.99)
    assert body["total_amount"] == pytest.approx(round(subtotal + tax + 9.99, 2))


def test_adding_same_product_increments_quantity(client, cart):
    add_item(client, cart["session_id"], HEADPHONES_ID, 1)
    body = add_item(client, cart["session_id"], HEADPHONES_ID, 3).json()
    assert len(body["items"]) == 1
    assert body["items"][0]["quantity"] == 4


def test_add_item_creates_cart_for_new_session(client):
    session_id = f"new-session-{uuid.uuid4()}"
    response = add_item(client, session_id, COFFEE_MAKER_ID, 1)
    assert response.status_code == 200
    assert response.json()["session_id"] == session_id
    assert client.get(f"/api/cart/{session_id}").status_code == 200


def test_add_unknown_product_returns_404(client, cart):
    response = add_item(client, cart["session_id"], 99999, 1)
    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"


def test_update_item_quantity(client, cart):
    session_id = cart["session_id"]
    add_item(client, session_id, COFFEE_MAKER_ID, 1)
    response = client.put(f"/api/cart/{session_id}/items/{COFFEE_MAKER_ID}", json={"quantity": 5})
    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["quantity"] == 5
    assert body["subtotal"] == pytest.approx(COFFEE_MAKER_PRICE * 5)


def test_update_quantity_to_zero_removes_item(client, cart):
    session_id = cart["session_id"]
    add_item(client, session_id, COFFEE_MAKER_ID, 1)
    response = client.put(f"/api/cart/{session_id}/items/{COFFEE_MAKER_ID}", json={"quantity": 0})
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_update_item_not_in_cart_returns_404(client, cart):
    response = client.put(f"/api/cart/{cart['session_id']}/items/{COFFEE_MAKER_ID}", json={"quantity": 2})
    assert response.status_code == 404


def test_remove_item(client, cart):
    session_id = cart["session_id"]
    add_item(client, session_id, HEADPHONES_ID, 1)
    add_item(client, session_id, COFFEE_MAKER_ID, 1)
    response = client.delete(f"/api/cart/{session_id}/items/{HEADPHONES_ID}")
    assert response.status_code == 200
    assert response.json()["message"] == "Item removed from cart successfully"
    items = client.get(f"/api/cart/{session_id}").json()["items"]
    assert [item["product_id"] for item in items] == [COFFEE_MAKER_ID]


def test_remove_item_not_in_cart_returns_404(client, cart):
    response = client.delete(f"/api/cart/{cart['session_id']}/items/{HEADPHONES_ID}")
    assert response.status_code == 404


def test_clear_cart(client, cart):
    session_id = cart["session_id"]
    add_item(client, session_id, HEADPHONES_ID, 1)
    add_item(client, session_id, COFFEE_MAKER_ID, 2)
    response = client.delete(f"/api/cart/{session_id}")
    assert response.status_code == 200
    assert response.json()["message"] == "Cart cleared successfully"
    assert client.get(f"/api/cart/{session_id}").json()["items"] == []


def test_clear_unknown_cart_returns_404(client):
    assert client.delete(f"/api/cart/{uuid.uuid4()}").status_code == 404


def test_checkout_success(client, cart, checkout_payload):
    session_id = cart["session_id"]
    add_item(client, session_id, HEADPHONES_ID, 2)
    response = client.post(f"/api/cart/{session_id}/checkout", json=checkout_payload)
    assert response.status_code == 200, response.text
    body = response.json()

    order = body["order"]
    uuid.UUID(order["id"])
    assert order["order_number"].startswith("ORD-")
    assert order["customer_email"] == checkout_payload["customer_email"]
    assert order["status"] == "confirmed"
    assert order["items"][0]["product_name"] == "Wireless Headphones"
    assert order["items"][0]["quantity"] == 2
    subtotal = HEADPHONES_PRICE * 2
    assert order["total_amount"] == pytest.approx(round(subtotal + round(subtotal * 0.08, 2) + 9.99, 2))

    payment = body["payment"]
    assert payment["status"] == "processed"
    assert payment["card_brand"] == "Visa"
    assert payment["last_four"] == "1111"

    # The cart is emptied once the order is placed.
    assert client.get(f"/api/cart/{session_id}").json()["items"] == []


def test_checkout_empty_cart_returns_400(client, cart, checkout_payload):
    response = client.post(f"/api/cart/{cart['session_id']}/checkout", json=checkout_payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Cart is empty"


def test_checkout_unknown_cart_returns_404(client, checkout_payload):
    response = client.post(f"/api/cart/{uuid.uuid4()}/checkout", json=checkout_payload)
    assert response.status_code == 404


@pytest.mark.parametrize("missing_field", ["customer_email", "customer_name"])
def test_checkout_requires_customer_details(client, cart, checkout_payload, missing_field):
    add_item(client, cart["session_id"], HEADPHONES_ID, 1)
    del checkout_payload[missing_field]
    response = client.post(f"/api/cart/{cart['session_id']}/checkout", json=checkout_payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Customer email and name are required"


@pytest.mark.parametrize("missing_field", ["card_number", "expiry_date", "cvv"])
def test_checkout_requires_payment_details(client, cart, checkout_payload, missing_field):
    add_item(client, cart["session_id"], HEADPHONES_ID, 1)
    del checkout_payload[missing_field]
    response = client.post(f"/api/cart/{cart['session_id']}/checkout", json=checkout_payload)
    assert response.status_code == 400
    assert "Complete payment information is required" in response.json()["detail"]


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("card_number", "4111111111111112", "Invalid card number"),
        ("expiry_date", "01/20", "Invalid or expired card"),
        ("cvv", "12", "Invalid CVV"),
    ],
)
def test_checkout_rejects_invalid_payment(client, cart, checkout_payload, field, value, error):
    session_id = cart["session_id"]
    add_item(client, session_id, HEADPHONES_ID, 1)
    checkout_payload[field] = value
    response = client.post(f"/api/cart/{session_id}/checkout", json=checkout_payload)
    assert response.status_code == 400
    assert response.json()["detail"] == f"Payment failed: {error}"
    # A failed payment leaves the cart intact.
    assert len(client.get(f"/api/cart/{session_id}").json()["items"]) == 1
