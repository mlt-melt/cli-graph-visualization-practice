from __future__ import annotations

from typing import Dict, Set, List, Tuple, Callable, Optional

# Types
DependencyProvider = Callable[[str], List[Tuple[str, str]]]  # package_id -> [(dep_id, version), ...]


class DependencyGraph:
    """
    Graph of package dependencies built using iterative DFS.
    Supports cycle detection and transitive dependency resolution.
    """

    def __init__(self):
        # nodes: package_id -> Set[dependency_id]
        self.nodes: Dict[str, Set[str]] = {}
        # cycles: list of cycle paths detected during DFS
        self.cycles: List[List[str]] = []

    def build_graph_dfs(
        self,
        root_package: str,
        dependency_provider: DependencyProvider,
        max_depth: int = 100,
    ) -> None:
        """
        Build full transitive dependency graph using iterative DFS (no recursion).
        Detects and records cycles.

        Args:
            root_package: starting package to resolve
            dependency_provider: callable that returns direct dependencies for a package
            max_depth: maximum depth to prevent infinite loops in malformed graphs
        """
        # State tracking
        visited: Set[str] = set()
        # Stack: (package_id, depth, parent_chain, is_processing)
        # is_processing=False means we need to explore this node
        # is_processing=True means we're backtracking (children explored)
        stack: List[Tuple[str, int, List[str], bool]] = [(root_package, 0, [], False)]
        # Track nodes currently in the DFS path for cycle detection
        path_set: Set[str] = set()

        while stack:
            pkg_id, depth, parent_chain, is_processing = stack.pop()

            if depth > max_depth:
                continue

            if is_processing:
                # Backtracking: remove from path
                path_set.discard(pkg_id)
                continue

            # If already fully visited, skip
            if pkg_id in visited:
                # But check if it's in current path (cycle)
                if pkg_id in path_set:
                    # Found a cycle
                    cycle_start_idx = parent_chain.index(pkg_id)
                    cycle_path = parent_chain[cycle_start_idx:] + [pkg_id]
                    if cycle_path not in self.cycles:
                        self.cycles.append(cycle_path)
                continue

            # Mark as visited and add to current path
            visited.add(pkg_id)
            path_set.add(pkg_id)
            new_chain = parent_chain + [pkg_id]

            # Initialize node in graph if not present
            if pkg_id not in self.nodes:
                self.nodes[pkg_id] = set()

            # Get direct dependencies
            try:
                direct_deps = dependency_provider(pkg_id)
            except Exception:
                # If provider fails, treat as no dependencies
                direct_deps = []

            # Push backtrack marker first (will be processed after children)
            stack.append((pkg_id, depth, parent_chain, True))

            # Add edges and push children onto stack
            for dep_id, _version in direct_deps:
                self.nodes[pkg_id].add(dep_id)
                # Push child for exploration
                stack.append((dep_id, depth + 1, new_chain, False))

    def node_count(self) -> int:
        return len(self.nodes)

    def edge_count(self) -> int:
        return sum(len(deps) for deps in self.nodes.values())

    def has_cycles(self) -> bool:
        return len(self.cycles) > 0

    def get_all_dependencies(self, package_id: str) -> Set[str]:
        """Get all transitive dependencies of a package (BFS or direct lookup)."""
        if package_id not in self.nodes:
            return set()
        visited = set()
        queue = [package_id]
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            for dep in self.nodes.get(current, []):
                if dep not in visited:
                    queue.append(dep)
        visited.discard(package_id)  # exclude self
        return visited
