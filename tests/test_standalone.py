import json
import tempfile
import unittest
from pathlib import Path

from verifiers.common import strict_json_loads
from verifiers.standalone_verify import load_strict


class StandaloneTests(unittest.TestCase):
    def test_boolean_integer_is_rejected(self):
        from verifiers.standalone_verify import verify_finite

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.json"
            path.write_text('{"schema":"erd169.finite.v1","k":true}', encoding="utf-8")
            with self.assertRaises(Exception):
                verify_finite(load_strict(path))

    def test_duplicate_keys_are_rejected(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            handle.write('{"schema":"x","schema":"y"}')
            path = Path(handle.name)
        try:
            with self.assertRaises(Exception):
                load_strict(path)
        finally:
            path.unlink()

    def test_float_is_rejected(self):
        with self.assertRaises(Exception):
            strict_json_loads('{"x": 1.0}')

    def test_manifest_has_valid_entries(self):
        path = Path(__file__).resolve().parents[1] / "certificates" / "MANIFEST.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        self.assertIsInstance(manifest.get("certificates"), list)
        self.assertTrue(manifest["certificates"])


if __name__ == "__main__":
    unittest.main()
