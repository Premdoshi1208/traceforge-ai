def validate_inventory(response, quantity):
    """Check that the inventory service can fulfill the requested quantity."""
    available = response["stock"]["available"] if "stock" in response else response["available"]
    if available < quantity:
        raise ValueError("insufficient inventory")
    return True
