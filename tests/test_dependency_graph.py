import unittest
from pathlib import Path

from dependency_graph import DependencyGraph
from test_repo import parse_test_repo, create_test_dependency_provider


class TestDependencyGraph(unittest.TestCase):
    def test_simple_chain(self):
        """Test linear dependency chain A -> B -> C"""
        repo_data = {"A": [("B", "*")], "B": [("C", "*")], "C": []}
        provider = create_test_dependency_provider(repo_data)
        graph = DependencyGraph()
        graph.build_graph_dfs("A", provider)

        self.assertEqual(graph.node_count(), 3)
        self.assertEqual(graph.edge_count(), 2)
        self.assertFalse(graph.has_cycles())
        self.assertIn("B", graph.nodes["A"])
        self.assertIn("C", graph.nodes["B"])

    def test_cycle_detection(self):
        """Test cycle detection: A -> B -> C -> A"""
        repo_data = {"A": [("B", "*")], "B": [("C", "*")], "C": [("A", "*")]}
        provider = create_test_dependency_provider(repo_data)
        graph = DependencyGraph()
        graph.build_graph_dfs("A", provider)

        self.assertEqual(graph.node_count(), 3)
        self.assertEqual(graph.edge_count(), 3)
        self.assertTrue(graph.has_cycles())
        self.assertEqual(len(graph.cycles), 1)
        cycle = graph.cycles[0]
        # Cycle should be A -> B -> C -> A
        self.assertEqual(cycle, ["A", "B", "C", "A"])

    def test_diamond_pattern(self):
        """Test diamond: A depends on B and C, both depend on D"""
        repo_data = {
            "A": [("B", "*"), ("C", "*")],
            "B": [("D", "*")],
            "C": [("D", "*")],
            "D": [],
        }
        provider = create_test_dependency_provider(repo_data)
        graph = DependencyGraph()
        graph.build_graph_dfs("A", provider)

        self.assertEqual(graph.node_count(), 4)
        self.assertEqual(graph.edge_count(), 4)  # A->B, A->C, B->D, C->D
        self.assertFalse(graph.has_cycles())
        # Check transitive dependencies
        all_deps = graph.get_all_dependencies("A")
        self.assertIn("B", all_deps)
        self.assertIn("C", all_deps)
        self.assertIn("D", all_deps)

    def test_complex_graph(self):
        """Test complex multi-level graph"""
        repo_data = {
            "A": [("B", "*"), ("C", "*")],
            "B": [("D", "*"), ("E", "*")],
            "C": [("E", "*")],
            "D": [],
            "E": [("F", "*")],
            "F": [],
        }
        provider = create_test_dependency_provider(repo_data)
        graph = DependencyGraph()
        graph.build_graph_dfs("A", provider)

        self.assertEqual(graph.node_count(), 6)
        self.assertEqual(graph.edge_count(), 6)
        self.assertFalse(graph.has_cycles())
        # A should transitively depend on all others
        all_deps = graph.get_all_dependencies("A")
        self.assertEqual(len(all_deps), 5)  # B, C, D, E, F

    def test_empty_graph(self):
        """Test package with no dependencies"""
        repo_data = {"A": []}
        provider = create_test_dependency_provider(repo_data)
        graph = DependencyGraph()
        graph.build_graph_dfs("A", provider)

        self.assertEqual(graph.node_count(), 1)
        self.assertEqual(graph.edge_count(), 0)
        self.assertFalse(graph.has_cycles())

    def test_parse_test_repo_file(self):
        """Test parsing test repository from file"""
        # Create a minimal test file
        import tempfile

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt", encoding="utf-8"
        ) as f:
            f.write("A: B C\n")
            f.write("B: D\n")
            f.write("C:\n")
            f.write("D:\n")
            temp_path = Path(f.name)

        try:
            repo_data = parse_test_repo(temp_path)
            self.assertIn("A", repo_data)
            self.assertEqual(len(repo_data["A"]), 2)
            self.assertEqual(repo_data["A"], [("B", "*"), ("C", "*")])
            self.assertEqual(repo_data["B"], [("D", "*")])
            self.assertEqual(repo_data["C"], [])
        finally:
            temp_path.unlink()


if __name__ == "__main__":
    unittest.main()
