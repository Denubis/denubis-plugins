from decimal import Decimal


def discounted_price(price: Decimal, discount: Decimal) -> Decimal:
    return price * (Decimal("1") - discount)
