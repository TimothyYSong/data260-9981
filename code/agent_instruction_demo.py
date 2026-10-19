
"""Demonstrate compliance with AGENT.md instructions."""


def format_inspection_record(
    restaurant_name: str,
    inspection_type: str,
    status: str,
) -> str:
    """Format a validated restaurant inspection as one bullet."""
    if not isinstance(restaurant_name, str):
        raise TypeError("Restaurant name must be a string")

    if not restaurant_name.strip():
        raise ValueError("Restaurant name cannot be empty")

    valid_types = {"routine", "follow_up", "complaint"}
    valid_statuses = {"pending", "passed", "failed"}

    if inspection_type not in valid_types:
        raise ValueError("Invalid inspection type")

    if status not in valid_statuses:
        raise ValueError("Invalid inspection status")

    return (
        f"- Restaurant: {restaurant_name.strip()}; "
        f"Inspection type: {inspection_type}; "
        f"Status: {status}"
    )
