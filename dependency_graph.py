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

    def get_reverse_dependencies(self, target_package: str) -> Set[str]:
        """
        Find all packages that depend on target_package (directly or transitively).
        Uses iterative traversal (non-recursive).
        
        Returns set of package IDs that have target_package in their dependency tree.
        """
        reverse_deps: Set[str] = set()
        
        # Check each node in the graph
        for pkg_id in self.nodes:
            if pkg_id == target_package:
                continue
            
            # Use iterative DFS to check if target is reachable from pkg_id
            visited: Set[str] = set()
            stack = [pkg_id]
            found = False
            
            while stack and not found:
                current = stack.pop()
                if current in visited:
                    continue
                visited.add(current)
                
                # Check if we reached the target
                if current == target_package:
                    reverse_deps.add(pkg_id)
                    found = True
                    break
                
                # Add children to stack
                for dep in self.nodes.get(current, []):
                    if dep not in visited:
                        stack.append(dep)
        
        return reverse_deps

    def export_to_d2(self) -> str:
        """
        Export dependency graph to D2 diagram language format.
        Returns a string containing the D2 diagram definition.
        """
        lines = []
        lines.append("# Dependency Graph")
        lines.append("direction: down")
        lines.append("")
        
        # Add all edges
        for pkg_id, deps in sorted(self.nodes.items()):
            for dep in sorted(deps):
                lines.append(f"{pkg_id} -> {dep}")
        
        # Highlight cycles if present
        if self.cycles:
            lines.append("")
            lines.append("# Cycles detected:")
            for i, cycle in enumerate(self.cycles):
                lines.append(f"# Cycle {i+1}: {' -> '.join(cycle)}")
                # Mark cycle edges in red
                for j in range(len(cycle) - 1):
                    lines.append(f"{cycle[j]} -> {cycle[j+1]}: {{style.stroke: red; style.stroke-width: 3}}")
        
        return "\n".join(lines)

    def format_as_ascii_tree(self, root_package: str) -> str:
        """
        Format dependency graph as ASCII tree starting from root_package.
        Uses box-drawing characters for tree structure.
        Detects and marks circular references.
        """
        if root_package not in self.nodes:
            return f"Package '{root_package}' not found in graph"
        
        lines = []
        visited_in_path: Set[str] = set()
        
        def render_tree(pkg: str, prefix: str, is_last: bool, path: Set[str]):
            # Detect circular reference
            if pkg in path:
                lines.append(f"{prefix}{'└── ' if is_last else '├── '}{pkg} [CIRCULAR]")
                return
            
            lines.append(f"{prefix}{'└── ' if is_last else '├── '}{pkg}")
            
            deps = sorted(self.nodes.get(pkg, []))
            if not deps:
                return
            
            new_path = path | {pkg}
            for i, dep in enumerate(deps):
                is_last_dep = (i == len(deps) - 1)
                extension = "    " if is_last else "│   "
                render_tree(dep, prefix + extension, is_last_dep, new_path)
        
        # Start rendering from root
        render_tree(root_package, "", True, set())
        return "\n".join(lines)
