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

    def test_reverse_dependencies_simple(self):
        """Test reverse dependencies in linear chain A -> B -> C"""
        repo_data = {"A": [("B", "*")], "B": [("C", "*")], "C": []}
        provider = create_test_dependency_provider(repo_data)
        graph = DependencyGraph()
        graph.build_graph_dfs("A", provider)

        # C is depended on by B
        reverse_c = graph.get_reverse_dependencies("C")
        self.assertIn("B", reverse_c)
        self.assertIn("A", reverse_c)  # A transitively depends on C

        # B is depended on by A
        reverse_b = graph.get_reverse_dependencies("B")
        self.assertIn("A", reverse_b)

        # A has no reverse dependencies
        reverse_a = graph.get_reverse_dependencies("A")
        self.assertEqual(len(reverse_a), 0)

    def test_reverse_dependencies_diamond(self):
        """Test reverse dependencies in diamond: A depends on B and C, both depend on D"""
        repo_data = {
            "A": [("B", "*"), ("C", "*")],
            "B": [("D", "*")],
            "C": [("D", "*")],
            "D": [],
        }
        provider = create_test_dependency_provider(repo_data)
        graph = DependencyGraph()
        graph.build_graph_dfs("A", provider)

        # D is depended on by A (transitively), B, and C
        reverse_d = graph.get_reverse_dependencies("D")
        self.assertIn("A", reverse_d)
        self.assertIn("B", reverse_d)
        self.assertIn("C", reverse_d)
        self.assertEqual(len(reverse_d), 3)

        # B and C are depended on by A
        reverse_b = graph.get_reverse_dependencies("B")
        self.assertIn("A", reverse_b)

        reverse_c = graph.get_reverse_dependencies("C")
        self.assertIn("A", reverse_c)

    def test_reverse_dependencies_with_cycle(self):
        """Test reverse dependencies with a cycle A -> B -> C -> A"""
        repo_data = {"A": [("B", "*")], "B": [("C", "*")], "C": [("A", "*")]}
        provider = create_test_dependency_provider(repo_data)
        graph = DependencyGraph()
        graph.build_graph_dfs("A", provider)

        # In a cycle, all nodes depend on each other transitively
        reverse_a = graph.get_reverse_dependencies("A")
        self.assertIn("B", reverse_a)
        self.assertIn("C", reverse_a)

        reverse_b = graph.get_reverse_dependencies("B")
        self.assertIn("A", reverse_b)
        self.assertIn("C", reverse_b)

        reverse_c = graph.get_reverse_dependencies("C")
        self.assertIn("A", reverse_c)
        self.assertIn("B", reverse_c)

    def test_reverse_dependencies_complex(self):
        """Test reverse dependencies in complex graph"""
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

        # F is depended on by E, B, C, and A (transitively)
        reverse_f = graph.get_reverse_dependencies("F")
        self.assertIn("E", reverse_f)
        self.assertIn("B", reverse_f)
        self.assertIn("C", reverse_f)
        self.assertIn("A", reverse_f)

        # E is depended on by B, C, and A
        reverse_e = graph.get_reverse_dependencies("E")
        self.assertIn("B", reverse_e)
        self.assertIn("C", reverse_e)
        self.assertIn("A", reverse_e)

        # D is only depended on by B and A
        reverse_d = graph.get_reverse_dependencies("D")
        self.assertIn("B", reverse_d)
        self.assertIn("A", reverse_d)
        self.assertNotIn("C", reverse_d)  # C does not depend on D

    def test_export_to_d2(self):
        """Test D2 diagram export"""
        repo_data = {"A": [("B", "*")], "B": [("C", "*")], "C": []}
        provider = create_test_dependency_provider(repo_data)
        graph = DependencyGraph()
        graph.build_graph_dfs("A", provider)

        d2_output = graph.export_to_d2()
        self.assertIn("A -> B", d2_output)
        self.assertIn("B -> C", d2_output)
        self.assertIn("direction: down", d2_output)

    def test_export_to_d2_with_cycle(self):
        """Test D2 export with cycle highlighting"""
        repo_data = {"A": [("B", "*")], "B": [("C", "*")], "C": [("A", "*")]}
        provider = create_test_dependency_provider(repo_data)
        graph = DependencyGraph()
        graph.build_graph_dfs("A", provider)

        d2_output = graph.export_to_d2()
        self.assertIn("A -> B", d2_output)
        self.assertIn("# Cycles detected:", d2_output)
        self.assertIn("style.stroke: red", d2_output)

    def test_ascii_tree_simple(self):
        """Test ASCII tree formatting for simple chain"""
        repo_data = {"A": [("B", "*")], "B": [("C", "*")], "C": []}
        provider = create_test_dependency_provider(repo_data)
        graph = DependencyGraph()
        graph.build_graph_dfs("A", provider)

        tree = graph.format_as_ascii_tree("A")
        self.assertIn("└── A", tree)
        self.assertIn("└── B", tree)
        self.assertIn("└── C", tree)

    def test_ascii_tree_with_cycle(self):
        """Test ASCII tree marks circular references"""
        repo_data = {"A": [("B", "*")], "B": [("C", "*")], "C": [("A", "*")]}
        provider = create_test_dependency_provider(repo_data)
        graph = DependencyGraph()
        graph.build_graph_dfs("A", provider)

        tree = graph.format_as_ascii_tree("A")
        self.assertIn("[CIRCULAR]", tree)

    def test_ascii_tree_diamond(self):
        """Test ASCII tree for diamond pattern"""
        repo_data = {
            "A": [("B", "*"), ("C", "*")],
            "B": [("D", "*")],
            "C": [("D", "*")],
            "D": [],
        }
        provider = create_test_dependency_provider(repo_data)
        graph = DependencyGraph()
        graph.build_graph_dfs("A", provider)

        tree = graph.format_as_ascii_tree("A")
        self.assertIn("├── B", tree)
        self.assertIn("└── C", tree)
        self.assertIn("│", tree)  # Should have vertical lines for tree structure


if __name__ == "__main__":
    unittest.main()
