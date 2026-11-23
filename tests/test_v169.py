import unittest

from verifiers.common import CertificateError
from verifiers.v169 import verify_digitset, verify_finite


class V169Tests(unittest.TestCase):
    def test_valid_finite_set(self):
        certificate = {
            "schema": "erd169.finite.v1",
            "k": "3",
            "N": "3",
            "members": ["1", "2"],
            "score": {"num": "3", "den": "2"},
        }
        result = verify_finite(certificate)
        self.assertEqual(result["score"], {"num": "3", "den": "2"})

    def test_rejects_arithmetic_progression(self):
        certificate = {
            "schema": "erd169.finite.v1",
            "k": "4",
            "N": "8",
            "members": ["2", "4", "6", "8"],
            "score": {"num": "15", "den": "8"},
        }
        with self.assertRaises(CertificateError):
            verify_finite(certificate)

    def test_rejects_integer_instead_of_decimal_string(self):
        certificate = {
            "schema": "erd169.finite.v1",
            "k": 3,
            "N": "3",
            "members": ["1", "2"],
            "score": {"num": "3", "den": "2"},
        }
        with self.assertRaises(CertificateError):
            verify_finite(certificate)

    def test_rejects_wrong_score(self):
        certificate = {
            "schema": "erd169.finite.v1",
            "k": "3",
            "N": "3",
            "members": ["1", "2"],
            "score": {"num": "7", "den": "4"},
        }
        with self.assertRaises(CertificateError):
            verify_finite(certificate)

    def test_rejects_unknown_field(self):
        certificate = {
            "schema": "erd169.finite.v1",
            "k": "3",
            "N": "3",
            "members": ["1", "2"],
            "score": {"num": "3", "den": "2"},
            "unexpected": "0",
        }
        with self.assertRaises(CertificateError):
            verify_finite(certificate)

    def test_rejects_duplicate_members(self):
        certificate = {
            "schema": "erd169.finite.v1",
            "k": "3",
            "N": "3",
            "members": ["1", "1"],
            "score": {"num": "1", "den": "1"},
        }
        with self.assertRaises(CertificateError):
            verify_finite(certificate)

    def test_rejects_boolean_k(self):
        certificate = {
            "schema": "erd169.finite.v1",
            "k": True,
            "N": "3",
            "members": ["1", "2"],
            "score": {"num": "3", "den": "2"},
        }
        with self.assertRaises(CertificateError):
            verify_finite(certificate)

    def test_rejects_boolean_score_component(self):
        certificate = {
            "schema": "erd169.finite.v1",
            "k": "3",
            "N": "3",
            "members": ["1", "2"],
            "score": {"num": True, "den": "2"},
        }
        with self.assertRaises(CertificateError):
            verify_finite(certificate)


if __name__ == "__main__":
    unittest.main()
