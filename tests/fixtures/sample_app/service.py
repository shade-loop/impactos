<<<<<<< HEAD
from sample_app.utils import format_name, calculate_discount

class UserService:
    def get_user(self, name: str) -> dict:
        return {"name": format_name(name)}
    
    def apply_offer(self, price: float, pct: float) -> float:
        return calculate_discount(price, pct)
=======
"""
sample_app.service
~~~~~~~~~~~~~~~~~~

Business-logic layer.  Imports from both ``sample_app.utils`` and
``sample_app.models``.
"""

from sample_app.models import Product, User
from sample_app.utils import format_product, format_user


def get_user_summary(user: User) -> str:
    """Return a formatted summary for a single user."""
    label = format_user(user)
    return f"Summary: {label}"


def get_product_summary(product: Product) -> str:
    """Return a formatted summary for a single product."""
    label = format_product(product)
    return f"Summary: {label}"


def get_catalogue_report(users: list[User], products: list[Product]) -> str:
    """Build a combined report of users and products."""
    user_lines = [format_user(u) for u in users]
    product_lines = [format_product(p) for p in products]
    return "\n".join(user_lines + product_lines)
>>>>>>> origin/main
