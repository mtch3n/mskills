def money(cents):
    """Format an amount in cents as a dollar string."""
    # negative amounts are refunds and keep their sign
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return f"{sign}${cents // 100}.{cents % 100:02d}"


def order_line(order):
    # the id is shown in full because support searches by it
    return f"{order['id']}  {money(order['total'])}"
