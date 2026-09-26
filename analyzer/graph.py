<<<<<<< HEAD
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
=======
"""
analyzer.graph
~~~~~~~~~~~~~~

In-memory directed dependency graph.

Stores nodes and edges in plain Python data structures.  Two adjacency
indices — ``_adj`` (forward) and ``_radj`` (reverse) — are maintained
alongside the canonical edge list so that both dependency traversal and
blast-radius (dependents) traversal run in O(V + E) without rescanning
the edge list.

No external libraries are used.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class GraphNode:
    """A node in the dependency graph.

    Attributes:
        id:          Unique stable identifier for this node within a graph.
                     Convention: ``"<dotted.module>"`` for modules,
                     ``"<dotted.module>.<ClassName>"`` for classes,
                     ``"<dotted.module>.<func_name>"`` for functions.
        type:        Semantic category — one of ``"module"``, ``"class"``,
                     or ``"function"``.
        file_path:   Path to the source file that defines this symbol.
                     Empty string for synthetic or unresolvable nodes.
        symbol_name: Short (unqualified) name of the symbol.
    """

    id: str
    type: str  # "module" | "class" | "function"
    file_path: str
    symbol_name: str


@dataclass
class GraphEdge:
    """A directed edge between two nodes in the dependency graph.

    Attributes:
        source:       ID of the originating node.
        target:       ID of the destination node.
        relationship: Semantic label — one of ``"imports"``,
                      ``"defines_class"``, ``"defines_function"``,
                      or ``"calls"``.
    """

    source: str
    target: str
    relationship: str  # "imports" | "defines_class" | "defines_function" | "calls"


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------


class DependencyGraph:
    """Directed in-memory dependency graph with bidirectional traversal.

    The graph supports four query operations:

    Forward (dependency direction — "what does X use?"):
        - :meth:`find_direct_dependencies`
        - :meth:`find_indirect_dependencies`

    Reverse (blast-radius direction — "what uses X?"):
        - :meth:`find_direct_dependents`
        - :meth:`find_indirect_dependents`

    Internal storage
    ----------------
    ``_nodes``  — ``dict[str, GraphNode]``  — node registry (keyed by node ID)
    ``_edges``  — ``list[GraphEdge]``       — canonical edge list
    ``_adj``    — ``dict[str, list[str]]``  — forward adjacency index
                  (source → list of target IDs)
    ``_radj``   — ``dict[str, list[str]]``  — reverse adjacency index
                  (target → list of source IDs)

    ``_adj`` and ``_radj`` are index structures: they contain node ID strings
    only, not copies of nodes or edges, so no data is duplicated.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, GraphNode] = {}
        self._edges: list[GraphEdge] = []
        self._adj: dict[str, list[str]] = {}
        self._radj: dict[str, list[str]] = {}
        # Deduplication set: (source, target, relationship)
        self._edge_keys: set[tuple[str, str, str]] = set()

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add_node(self, node: GraphNode) -> None:
        """Add *node* to the graph.

        If a node with the same ``id`` already exists the call is a no-op
        (first write wins).

        Args:
            node: The :class:`GraphNode` to register.
        """
        if node.id not in self._nodes:
            self._nodes[node.id] = node

    def add_edge(self, edge: GraphEdge) -> None:
        """Add a directed edge and update both adjacency indices.

        Duplicate edges (same ``source``, ``target``, and ``relationship``)
        are silently ignored.

        Args:
            edge: The :class:`GraphEdge` to add.
        """
        key = (edge.source, edge.target, edge.relationship)
        if key in self._edge_keys:
            return

        self._edges.append(edge)
        self._edge_keys.add(key)

        # Update forward index
        self._adj.setdefault(edge.source, []).append(edge.target)

        # Update reverse index
        self._radj.setdefault(edge.target, []).append(edge.source)

    # ------------------------------------------------------------------
    # Basic accessors
    # ------------------------------------------------------------------

    def get_nodes(self) -> list[GraphNode]:
        """Return all nodes in the graph.

        Returns:
            A list of :class:`GraphNode` objects in insertion order.
        """
        return list(self._nodes.values())

    def get_edges(self) -> list[GraphEdge]:
        """Return all edges in the graph (canonical list, no copies).

        Returns:
            A list of :class:`GraphEdge` objects in insertion order.
        """
        return list(self._edges)

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Look up a node by its ID.

        Args:
            node_id: The unique node identifier.

        Returns:
            The :class:`GraphNode` if found, otherwise ``None``.
        """
        return self._nodes.get(node_id)

    # ------------------------------------------------------------------
    # Forward traversal — dependency direction
    # ------------------------------------------------------------------

    def find_direct_dependencies(self, node_id: str) -> list[GraphNode]:
        """Return nodes that *node_id* directly depends on (one hop outbound).

        Example: if ``main`` imports ``service``, calling this with
        ``"main"`` returns ``[<service node>]``.

        Args:
            node_id: ID of the source node.

        Returns:
            List of :class:`GraphNode` objects reachable in one step via
            outbound edges.  Nodes not present in the graph are omitted.
        """
        targets = self._adj.get(node_id, [])
        return [self._nodes[t] for t in targets if t in self._nodes]

    def find_indirect_dependencies(self, node_id: str) -> list[GraphNode]:
        """Return all nodes that *node_id* transitively depends on (BFS outbound).

        The starting node is excluded from the result.

        Args:
            node_id: ID of the source node.

        Returns:
            List of all :class:`GraphNode` objects reachable via outbound
            edges (transitive closure), in BFS order.
        """
        return self._bfs(node_id, self._adj)

    # ------------------------------------------------------------------
    # Reverse traversal — blast-radius direction
    # ------------------------------------------------------------------

    def find_direct_dependents(self, node_id: str) -> list[GraphNode]:
        """Return nodes that directly depend on *node_id* (one hop inbound).

        Example: if both ``service`` and ``main`` import ``utils``, calling
        this with ``"utils"`` returns ``[<service node>, <main node>]``.

        Args:
            node_id: ID of the target node.

        Returns:
            List of :class:`GraphNode` objects that have an outbound edge
            pointing to *node_id*.  Nodes not present in the graph are omitted.
        """
        sources = self._radj.get(node_id, [])
        return [self._nodes[s] for s in sources if s in self._nodes]

    def find_indirect_dependents(self, node_id: str) -> list[GraphNode]:
        """Return all nodes that transitively depend on *node_id* (BFS inbound).

        This is the **blast-radius** query: given a changed module, which
        other modules are potentially impacted?

        The starting node is excluded from the result.

        Args:
            node_id: ID of the changed node.

        Returns:
            List of all :class:`GraphNode` objects that transitively depend
            on *node_id*, in BFS order.
        """
        return self._bfs(node_id, self._radj)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _bfs(
        self, start: str, index: dict[str, list[str]]
    ) -> list[GraphNode]:
        """Generic BFS over *index* starting from *start*.

        Used by both ``find_indirect_dependencies`` (forward index ``_adj``)
        and ``find_indirect_dependents`` (reverse index ``_radj``).

        Args:
            start: Starting node ID (excluded from the result).
            index: Adjacency index to traverse (``_adj`` or ``_radj``).

        Returns:
            Ordered list of visited :class:`GraphNode` objects, excluding
            *start* itself.
        """
        visited: set[str] = {start}
        queue: deque[str] = deque(index.get(start, []))
        result: list[GraphNode] = []

        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            if current in self._nodes:
                result.append(self._nodes[current])
            for neighbour in index.get(current, []):
                if neighbour not in visited:
                    queue.append(neighbour)

        return result
>>>>>>> origin/main
