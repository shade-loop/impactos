"""
analyzer.parser
~~~~~~~~~~~~~~~

AST-based Python source file analyser.

Reads a single ``.py`` file and returns a :class:`ParsedModule` describing the
symbols that were found: imported modules, defined classes, defined functions,
and call expressions.  Only the standard-library ``ast`` module is used.
"""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ParsedModule:
    """Structured representation of symbols extracted from one Python file.

    Attributes:
        file_path:   Absolute path to the source file.
        module_name: Dotted module name derived from the repository root
                     (e.g. ``"sample_app.utils"``).
        imports:     Dotted names of every module imported by this file
                     (e.g. ``["sample_app.models", "os.path"]``).
        classes:     Names of all top-level and nested class definitions.
        functions:   Names of all function / async-function definitions
                     (includes methods inside classes).
        calls:       Names of every called callable as they appear in the
                     source (e.g. ``"format_user"``, ``"os.path.join"``).
    """

    file_path: str
    module_name: str
    imports: list[str] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)
    calls: list[str] = field(default_factory=list)


class _SymbolVisitor(ast.NodeVisitor):
    """Collects symbols from an AST by visiting each relevant node type.

    After calling :meth:`visit` on a module-level AST node the collected
    symbols are available via the ``imports``, ``classes``, ``functions``,
    and ``calls`` attributes.
    """

    def __init__(self) -> None:
        self.imports: list[str] = []
        self.classes: list[str] = []
        self.functions: list[str] = []
        self.calls: list[str] = []

    # ------------------------------------------------------------------
    # Import visitors
    # ------------------------------------------------------------------

    def visit_Import(self, node: ast.Import) -> None:  # noqa: N802
        """Handle ``import foo`` and ``import foo.bar``."""
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
        """Handle ``from foo import bar`` — record the *module* being imported."""
        if node.module:
            self.imports.append(node.module)
        self.generic_visit(node)

    # ------------------------------------------------------------------
    # Definition visitors
    # ------------------------------------------------------------------

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        """Record a class definition name and continue into its body."""
        self.classes.append(node.name)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        """Record a function/method definition name."""
        self.functions.append(node.name)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(  # noqa: N802
        self, node: ast.AsyncFunctionDef
    ) -> None:
        """Record an async function/method definition name."""
        self.functions.append(node.name)
        self.generic_visit(node)

    # ------------------------------------------------------------------
    # Call visitors
    # ------------------------------------------------------------------

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        """Record the callable name from a call expression.

        Handles:
        - ``name(...)``          → ``"name"``
        - ``obj.method(...)``    → ``"obj.method"``
        - ``a.b.c(...)``         → ``"a.b.c"``
        """
        call_name = _extract_call_name(node.func)
        if call_name:
            self.calls.append(call_name)
        self.generic_visit(node)


def _extract_call_name(func_node: ast.expr) -> str | None:
    """Return the textual name of a callable from its AST node, or ``None``.

    Args:
        func_node: The ``.func`` attribute of an :class:`ast.Call` node.

    Returns:
        A dotted name string, or ``None`` if the expression is too complex to
        represent as a simple name (e.g. a subscript or lambda).
    """
    if isinstance(func_node, ast.Name):
        return func_node.id
    if isinstance(func_node, ast.Attribute):
        owner = _extract_call_name(func_node.value)
        if owner:
            return f"{owner}.{func_node.attr}"
        return func_node.attr
    return None


def parse_file(path: Path) -> ParsedModule:
    """Parse a single Python source file and return its extracted symbols.

    On a syntax error the file is skipped gracefully: a warning is logged and
    an empty-but-valid :class:`ParsedModule` is returned so that the rest of
    the analysis is unaffected.

    Args:
        path: Absolute (or resolvable) path to a ``.py`` file.

    Returns:
        A :class:`ParsedModule` populated with the symbols found in *path*.
    """
    path = Path(path)
    module_name = path.stem  # caller should override with the full dotted name

    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("Could not read %s: %s", path, exc)
        return ParsedModule(file_path=str(path), module_name=module_name)

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        logger.warning("Syntax error in %s: %s", path, exc)
        return ParsedModule(file_path=str(path), module_name=module_name)

    visitor = _SymbolVisitor()
    visitor.visit(tree)

    return ParsedModule(
        file_path=str(path),
        module_name=module_name,
        imports=visitor.imports,
        classes=visitor.classes,
        functions=visitor.functions,
        calls=visitor.calls,
    )
