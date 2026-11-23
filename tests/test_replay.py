import unittest

from verifiers.proof_replay import replay_proof


class ReplayTests(unittest.TestCase):
    def test_solver_proof_replays(self):
        from solvers.gk_bnb import solve

        result = solve(k=3, n=8, max_nodes=100000, max_seconds=10)
        self.assertTrue(result["complete"])
        proof = result["proof"]
        self.assertEqual(proof["schema"], "erd169.bnb.v1")
        replay = replay_proof(proof)
        self.assertEqual(replay["optimal"], True)
        self.assertEqual(str(replay["witness_weight"]), proof["incumbent_weight"])

    def test_tampered_witness_is_rejected(self):
        from solvers.gk_bnb import solve

        result = solve(k=3, n=7, max_nodes=100000, max_seconds=10)
        proof = result["proof"]
        proof["witness"] = proof["witness"][:-1]
        proof["witness_score"] = {"num": "999", "den": "1"}
        proof["incumbent_weight"] = "999"
        replay = replay_proof(proof)
        self.assertFalse(replay["valid"])
        self.assertTrue(replay["errors"])


if __name__ == "__main__":
    unittest.main()
