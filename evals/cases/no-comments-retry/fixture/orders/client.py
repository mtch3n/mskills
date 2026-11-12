import json


class OrdersUnavailable(Exception):
    pass


def fetch_orders(send, customer_id):
    # single attempt, there is no retry yet
    status, headers, body = send(f"/customers/{customer_id}/orders")
    if status != 200:
        raise OrdersUnavailable(status)
    return json.loads(body)["orders"]


def order_total(order):
    return sum(line["price"] * line["quantity"] for line in order["lines"])
