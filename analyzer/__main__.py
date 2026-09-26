"""
analyzer.__main__
~~~~~~~~~~~~~~~~~

Entry point for ``python -m analyzer``.

Delegates to the existing CLI so that::

    python -m analyzer <command> ...

continues to work as before (Tasks 02–04 CLI).
"""
from analyzer.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
