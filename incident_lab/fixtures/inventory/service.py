def validate_inventory(response, quantity):
    """Check that the inventory service can fulfill the requested quantity."""
    available = response["available"]
    if available < quantity:
        raise ValueError("insufficient inventory")
    return True
