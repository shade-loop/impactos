# Utility functions for sample app
def format_name(name: str) -> str:
    return name.strip().title()

def calculate_discount(price: float, pct: float) -> float:
    return price * (1 - pct / 100)
