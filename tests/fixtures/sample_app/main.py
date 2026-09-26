<<<<<<< HEAD
from sample_app.service import UserService

def run():
    svc = UserService()
    print(svc.get_user("alice"))
=======
"""
sample_app.main
~~~~~~~~~~~~~~~

Entry point.  Imports from ``sample_app.service`` and calls its functions.
"""

from sample_app.service import get_catalogue_report, get_user_summary
from sample_app.models import User, Product


def run() -> None:
    """Execute the sample application."""
    alice = User(1, "Alice")
    widget = Product(42, "Widget", 9.99)

    print(get_user_summary(alice))
    print(get_catalogue_report([alice], [widget]))

>>>>>>> origin/main

if __name__ == "__main__":
    run()
