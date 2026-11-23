import ast
import unittest
from pathlib import Path


class NoFloatTests(unittest.TestCase):
    def test_verifiers_do_not_use_floating_point(self):
        root = Path(__file__).resolve().parents[1] / "verifiers"
        forbidden_calls = {"sqrt", "fsum"}
        forbidden_imports = {"numpy", "numpy.linalg", "decimal"}
        for path in root.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    self.assertNotIn(node.func.attr, forbidden_calls, path)
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertNotIn(alias.name, forbidden_imports, path)
                if isinstance(node, ast.ImportFrom) and node.module:
                    self.assertNotIn(node.module, forbidden_imports, path)
                if isinstance(node, ast.Constant) and isinstance(node.value, float):
                    self.fail(f"float literal in verifier: {path}:{node.lineno}")
                if isinstance(node, ast.Attribute) and node.attr in {"sqrt", "fsum"}:
                    self.fail(f"floating-point helper in verifier: {path}:{node.lineno}")


if __name__ == "__main__":
    unittest.main()
