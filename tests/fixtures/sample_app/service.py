from sample_app.utils import format_name, calculate_discount

class UserService:
    def get_user(self, name: str) -> dict:
        return {"name": format_name(name)}
    
    def apply_offer(self, price: float, pct: float) -> float:
        return calculate_discount(price, pct)
