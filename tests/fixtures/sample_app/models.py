"""
sample_app.models
~~~~~~~~~~~~~~~~~

Domain model definitions.  No imports from sibling modules.
"""


class User:
    """Represents a system user."""

    def __init__(self, user_id: int, name: str) -> None:
        self.user_id = user_id
        self.name = name

    def display_name(self) -> str:
        """Return a formatted display name."""
        return f"User({self.user_id}): {self.name}"


class Product:
    """Represents a product in the catalogue."""

    def __init__(self, product_id: int, title: str, price: float) -> None:
        self.product_id = product_id
        self.title = title
        self.price = price

    def summary(self) -> str:
        """Return a one-line product summary."""
        return f"Product({self.product_id}): {self.title} @ {self.price:.2f}"
