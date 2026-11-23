import unittest

from verifiers.common import CertificateError
from verifiers.v686 import verify_null, verify_representation
from solvers.s686_divisor import solve_square


class V686Tests(unittest.TestCase):
    def test_known_witnesses(self):
        witnesses = [
            (9, 3, 11, 25),
            (16, 3, 4, 13),
            (100, 2, 1, 23),
        ]
        for n_value, k, n, m in witnesses:
            certificate = {
                "schema": "erd686.rep.v1",
                "N": str(n_value),
                "k": str(k),
                "n": str(n),
                "m": str(m),
            }
            verify_representation(certificate)

    def test_rejects_n_zero(self):
        certificate = {
            "schema": "erd686.rep.v1",
            "N": "6",
            "k": "2",
            "n": "0",
            "m": "4",
        }
        with self.assertRaises(CertificateError):
            verify_representation(certificate)

    def test_rejects_boundary_violation(self):
        certificate = {
            "schema": "erd686.rep.v1",
            "N": "6",
            "k": "2",
            "n": "1",
            "m": "2",
        }
        with self.assertRaises(CertificateError):
            verify_representation(certificate)

    def test_rejects_unknown_field(self):
        certificate = {
            "schema": "erd686.rep.v1",
            "N": "9",
            "k": "3",
            "n": "11",
            "m": "25",
            "unexpected": "0",
        }
        with self.assertRaises(CertificateError):
            verify_representation(certificate)

    def test_rejects_m_below_n_plus_k(self):
        certificate = {
            "schema": "erd686.rep.v1",
            "N": "6",
            "k": "2",
            "n": "1",
            "m": "2",
        }
        with self.assertRaises(CertificateError):
            verify_representation(certificate)

    def test_rejects_k_one(self):
        certificate = {
            "schema": "erd686.rep.v1",
            "N": "9",
            "k": "1",
            "n": "11",
            "m": "25",
        }
        with self.assertRaises(CertificateError):
            verify_representation(certificate)

    def test_squares_four_and_twentyfive_have_no_k2_or_k4(self):
        for s in (4, 25):
            decision = solve_square(s)
            self.assertEqual(decision["witnesses"]["2"], [])
            self.assertEqual(decision["witnesses"]["4"], [])

    def test_null_certificate_is_accepted(self):
        certificate = {
            "schema": "erd686.null.v1",
            "s": "4",
            "k_set": ["2", "4"],
            "method": "divisor_complete",
            "box": None,
            "domain": "n>=1",
        }
        self.assertTrue(verify_null(certificate)["valid"])


if __name__ == "__main__":
    unittest.main()
