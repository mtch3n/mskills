from orders.format import money


def test_money():
    assert money(1234) == "$12.34"
    assert money(-5) == "-$0.05"
