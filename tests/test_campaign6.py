import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from solvers.gk_bnb import solve
from verifiers import standalone_verify as st
from verifiers.proof_replay import replay_proof


class Campaign6SecurityAndParityTests(unittest.TestCase):
    def test_bitmask_replay_differential_on_valid_and_mutated_proofs(self):
        proof = solve(3, 9, max_nodes=100000, max_seconds=10)["proof"]
        self.assertTrue(st.replay(proof)["valid"])
        self.assertTrue(replay_proof(proof)["valid"])

        mutations = [
            lambda p: p["tree"].pop(),
            lambda p: p.update(incumbent_weight=str(int(p["incumbent_weight"]) + 1)),
            lambda p: p["tree"][0].update(j="999"),
            lambda p: p["tree"].append({"op": "leaf", "status": "feasible"}),
            lambda p: p.update(witness=["1", "2", "3"]),
        ]
        for mutate in mutations:
            bad = copy.deepcopy(proof)
            mutate(bad)
            self.assertFalse(replay_proof(bad)["valid"])
            with self.assertRaises(st.BadCertificate):
                st.replay(bad)

        # Mutate a prune node that relies on AP deductions, or inject overlapping APs.
        prune_idx = next(
            i for i, n in enumerate(proof["tree"]) if n.get("op") == "prune" and n.get("aps")
        )
        bad_overlap = copy.deepcopy(proof)
        bad_overlap["tree"][prune_idx]["aps"] = [bad_overlap["tree"][prune_idx]["aps"][0]] * 2
        self.assertFalse(replay_proof(bad_overlap)["valid"])
        with self.assertRaises(st.BadCertificate):
            st.replay(bad_overlap)

        # Also check a prune node where dropping aps causes bound > incumbent.
        for i, n in enumerate(proof["tree"]):
            if n.get("op") == "prune" and n.get("aps"):
                cand = copy.deepcopy(proof)
                cand["tree"][i]["aps"] = []
                if not replay_proof(cand)["valid"]:
                    with self.assertRaises(st.BadCertificate):
                        st.replay(cand)
                    break

    def test_memo_poisoning_stale_file_and_wrong_path_substitution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            good = {
                "schema": "erd169.finite.v1",
                "k": "3",
                "N": "3",
                "members": ["1", "2"],
                "score": {"num": "3", "den": "2"},
            }
            bad_ap = {
                "schema": "erd169.finite.v1",
                "k": "3",
                "N": "3",
                "members": ["1", "2", "3"],
                "score": {"num": "11", "den": "6"},
            }
            good_bytes = st.canonical_bytes(good)
            good_sha = hashlib.sha256(good_bytes).hexdigest()
            bad_bytes = st.canonical_bytes(bad_ap)
            bad_sha = hashlib.sha256(bad_bytes).hexdigest()

            (root / "good.json").write_bytes(good_bytes)
            (root / "bad.json").write_bytes(bad_bytes)

            with st.digest_run(root):
                # Failing verification must never populate the memo.
                res_bad = st.verify_entry({"path": "bad.json", "sha256": bad_sha}, root)
                self.assertFalse(res_bad["valid"])
                self.assertNotIn(("standalone", "erd169.finite.v1", bad_sha), st._DIGEST_INDEX.get()[3])

                # Valid verification populates memo, and wrong-path substitution fails.
                res_good = st.verify_entry({"path": "good.json", "sha256": good_sha}, root)
                self.assertTrue(res_good["valid"])
                wrong_path = st.verify_entry({"path": "bad.json", "sha256": good_sha}, root)
                self.assertFalse(wrong_path["valid"])
                self.assertIn("sha256 mismatch", wrong_path["error"])

                # Same-size / mid-run stale file modification must be caught.
                (root / "good.json").write_bytes(
                    st.canonical_bytes(
                        {
                            "schema": "erd169.finite.v1",
                            "k": "3",
                            "N": "3",
                            "members": ["1", "3"],
                            "score": {"num": "4", "den": "3"},
                        }
                    )
                )
                stale = st.verify_entry({"path": "good.json", "sha256": good_sha}, root)
                self.assertFalse(stale["valid"])
                self.assertIn("sha256 mismatch", stale["error"])

    def test_duplicate_keys_and_malformed_integers_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dup = root / "dup.json"
            dup.write_text('{"schema":"erd169.finite.v1","schema":"erd169.finite.v1"}', encoding="utf-8")
            with self.assertRaises(st.BadCertificate):
                st.load_strict(dup)
            for bad_int in ("01", "-1", 3, True):
                cert = {
                    "schema": "erd169.finite.v1",
                    "k": bad_int,
                    "N": "3",
                    "members": ["1", "2"],
                    "score": {"num": "3", "den": "2"},
                }
                with self.assertRaises(st.BadCertificate):
                    st.verify_finite(cert)

    def test_legacy_733_files_unchanged(self):
        baseline = json.loads(Path("benchmarks/c6_legacy_bytes.json").read_text())
        self.assertEqual(len(baseline["raw_sha256"]), 733)
        for rel_path, digest in baseline["raw_sha256"].items():
            self.assertEqual(
                hashlib.sha256((Path("certificates") / rel_path).read_bytes()).hexdigest(),
                digest,
                rel_path,
            )

    def test_campaign6_deliverables_and_hygiene(self):
        res = json.loads(Path("benchmarks/campaign6_results.json").read_text())
        self.assertEqual(res["prefix_endpoints"], {"3": 40, "4": 40, "5": 60, "6": 60})
        self.assertEqual(res["prefix_rows"], 200)
        self.assertEqual(res["manifest_entries"], {"MANIFEST.json": 755, "MANIFEST_DEEP.json": 2})
        self.assertTrue(res["default_under_10s"])

        m = json.loads(Path("benchmarks/c6_z125_measure.json").read_text())
        self.assertEqual(m["claim"], "none")
        self.assertFalse(m["gate_g1_passed"])
        self.assertFalse(Path("certificates/c6_z125_max.json").exists())

        prog = json.loads(Path("benchmarks/c6_z125_progress.json").read_text())
        self.assertEqual(prog["claim"], "none")

        timings = json.loads(Path("benchmarks/c6_timings.json").read_text())
        self.assertTrue(timings["all_default_under_10s"])
        self.assertEqual(len(timings["MANIFEST.json"]), 3)
        for run in timings["MANIFEST.json"]:
            self.assertLess(int(run["elapsed_ns"]), 10_000_000_000)

        for doc in (
            Path("README.md"),
            Path("CITATION.cff"),
            Path("docs/CAMPAIGN6_CHECKS.md"),
            Path("docs/CAMPAIGN6_REPORT_AR.md"),
            Path("docs/TRAPS.md"),
            Path("submissions/arxiv_note_draft.md"),
            Path("submissions/erdosproblems_PR_169.md"),
            Path("benchmarks/c6_profile.txt"),
        ):
            self.assertNotRegex(doc.read_text(), r"file://|/Volumes/|/Users/", str(doc))


if __name__ == "__main__":
    unittest.main()
