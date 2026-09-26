from collections import deque


class DependencyGraph:
    """Directed dependency graph.

    Edges go FROM importer TO imported.
    A "dependent" of module X is any module that imports X.
    """

    def __init__(self, imports: dict[str, set[str]]) -> None:
        # reverse_adj[module] = set of modules that import module
        self._reverse_adj: dict[str, set[str]] = {}

        for importer, imported_set in imports.items():
            # Ensure every importer has an entry even if nothing imports it
            if importer not in self._reverse_adj:
                self._reverse_adj[importer] = set()
            for imported in imported_set:
                if imported not in self._reverse_adj:
                    self._reverse_adj[imported] = set()
                self._reverse_adj[imported].add(importer)

    def get_direct_dependents(self, module: str) -> set[str]:
        """Return all modules that directly import the given module."""
        return set(self._reverse_adj.get(module, set()))

    def get_all_affected(
        self, changed_modules: list[str]
    ) -> tuple[list[str], list[str], int]:
        """BFS from changed_modules through the reverse dependency graph.

        Returns:
            direct_affected  – nodes at depth 1
            indirect_affected – nodes at depth 2+
            max_depth        – deepest depth reached (0 if nothing affected)
        """
        visited: set[str] = set(changed_modules)
        queue: deque[tuple[str, int]] = deque()

        for mod in changed_modules:
            for dep in self.get_direct_dependents(mod):
                if dep not in visited:
                    visited.add(dep)
                    queue.append((dep, 1))

        direct_affected: list[str] = []
        indirect_affected: list[str] = []
        max_depth = 0

        while queue:
            node, depth = queue.popleft()
            max_depth = max(max_depth, depth)

            if depth == 1:
                direct_affected.append(node)
            else:
                indirect_affected.append(node)

            for dep in self.get_direct_dependents(node):
                if dep not in visited:
                    visited.add(dep)
                    queue.append((dep, depth + 1))

        return direct_affected, indirect_affected, max_depth
