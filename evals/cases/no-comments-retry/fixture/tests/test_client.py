import json

from orders.client import OrdersUnavailable, fetch_orders, order_total


def ok(orders):
    return lambda path: (200, {}, json.dumps({"orders": orders}))


def test_fetch_returns_orders():
    assert fetch_orders(ok([{"id": "A1"}]), 7) == [{"id": "A1"}]


def test_fetch_raises_on_server_error():
    try:
        fetch_orders(lambda path: (500, {}, ""), 7)
    except OrdersUnavailable:
        return
    raise AssertionError("expected OrdersUnavailable")


def test_order_total():
    assert order_total({"lines": [{"price": 250, "quantity": 2}]}) == 500
