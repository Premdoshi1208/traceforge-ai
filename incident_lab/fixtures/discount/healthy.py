def calculate_total(subtotal, discount_percent):
    """Return an order total after applying the checkout discount."""
    return round(subtotal * (1 - float(discount_percent) / 100), 2)
