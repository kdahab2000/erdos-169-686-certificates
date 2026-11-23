import tempfile
import unittest
from pathlib import Path

from verifiers.common import CertificateError, canonical_json_bytes
from verifiers.proof_replay import replay_proof
from verifiers.v169 import verify_finite
from verifiers.v686 import verify_representation


class ParityTests(unittest.TestCase):
    def test_standalone_matches_lab_finite_verifier(self):
        from verifiers.standalone_verify import verify_certificate

        certificate = {
            "schema": "erd169.finite.v1",
            "k": "3",
            "N": "3",
            "members": ["1", "2"],
            "score": {"num": "3", "den": "2"},
        }
        self.assertEqual(
            verify_finite(certificate),
            verify_certificate(certificate),
        )

    def test_standalone_matches_lab_686_verifier(self):
        from verifiers.standalone_verify import verify_certificate

        certificate = {
            "schema": "erd686.rep.v1",
            "N": "9",
            "k": "3",
            "n": "11",
            "m": "25",
        }
        self.assertEqual(
            verify_representation(certificate),
            verify_certificate(certificate),
        )

    def test_standalone_rejects_duplicate_json_keys(self):
        from verifiers.standalone_verify import load_strict

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            handle.write('{"schema":"x","schema":"y"}')
            path = Path(handle.name)
        try:
            with self.assertRaises(Exception):
                load_strict(path)
        finally:
            path.unlink()


if __name__ == "__main__":
    unittest.main()
