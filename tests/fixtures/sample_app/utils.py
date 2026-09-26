<<<<<<< HEAD
# Utility functions for sample app
def format_name(name: str) -> str:
    return name.strip().title()

def calculate_discount(price: float, pct: float) -> float:
    return price * (1 - pct / 100)
=======
"""
sample_app.utils
~~~~~~~~~~~~~~~~

Utility helpers.  Imports from ``sample_app.models``.
"""

from sample_app.models import Product, User


def format_user(user: User) -> str:
    """Return a human-readable string for *user*."""
    return f"[{user.user_id}] {user.name}"


def format_product(product: Product) -> str:
    """Return a human-readable string for *product*."""
    return f"[{product.product_id}] {product.title} ({product.price:.2f})"
>>>>>>> origin/main
