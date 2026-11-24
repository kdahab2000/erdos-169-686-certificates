"""Bounded, offline Campaign 6 driver. Run phases from the worktree root."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from verifiers.common import canonical_json_bytes, write_json
from verifiers import proof_replay, standalone_verify as st, v169


def save(path: str | Path, value: object) -> None:
    Path(path).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def baseline() -> None:
    m1 = json.loads(Path("certificates/MANIFEST.json").read_text())["certificates"]
    m2 = json.loads(Path("certificates/MANIFEST_DEEP.json").read_text())["certificates"]
    p = Path("benchmarks/c6_legacy_bytes.json")
    if p.exists():
        data = json.loads(p.read_text())
        for rel, expected in data["raw_sha256"].items():
            actual = hashlib.sha256((Path("certificates") / rel).read_bytes()).hexdigest()
            assert actual == expected, f"legacy hash mismatch: {rel}"
        assert m1[: len(data["manifests"]["MANIFEST.json"])] == data["manifests"]["MANIFEST.json"]
        assert m2[: len(data["manifests"]["MANIFEST_DEEP.json"])] == data["manifests"]["MANIFEST_DEEP.json"]
        print(f"Verified {len(data['raw_sha256'])} legacy hashes")
        return
    files = sorted(
        str(x.relative_to("certificates"))
        for x in Path("certificates").rglob("*.json")
        if x.name not in ("MANIFEST.json", "MANIFEST_DEEP.json")
    )
    raw = {f: hashlib.sha256((Path("certificates") / f).read_bytes()).hexdigest() for f in files}
    save(p, {"raw_sha256": raw, "manifests": {"MANIFEST.json": m1, "MANIFEST_DEEP.json": m2}})
    print(f"Recorded {len(raw)} legacy hashes")


def z125_measure() -> None:
    from solvers.z125_fibre import measure_c6

    res = measure_c6(max_seconds_per_run=5, max_nodes=200000)
    save(
        "benchmarks/c6_z125_progress.json",
        {"schema": "local.c6.orbit_checkpoint.v1", "claim": "none", "orbits": []},
    )
    print("z125-measure gate_g1_passed=", res["gate_g1_passed"])


def z125_full() -> None:
    p = Path("benchmarks/c6_z125_measure.json")
    if not p.exists():
        raise ValueError("Run z125-measure first")
    m = json.loads(p.read_text())
    if not m.get("gate_g1_passed"):
        print("Gate G1 not passed; Z/125Z stays at 64 <= M <= 80; no certificate emitted.")
        return
    raise NotImplementedError("Gate G1 passed path requires sample & G2 check")


def prefixes() -> None:
    from solvers.gk_bnb import solve

    tables_path = Path("benchmarks/oeis_tables.json")
    tables = json.loads(tables_path.read_text())
    log_path = Path("benchmarks/c6_prefix.log")
    with log_path.open("a", encoding="utf-8") as log:
        for table in tables["tables"]:
            k = int(table["k"])
            if k not in (3, 4):
                continue
            start_n = int(table["endpoint"]) + 1
            for n in range(start_n, 41):
                t0 = time.monotonic_ns()
                r = solve(
                    k,
                    n,
                    max_seconds=20,
                    warm_start=list(map(int, table["rows"][-1]["members"])),
                )
                solve_ns = time.monotonic_ns() - t0
                line = f"k={k} N={n} complete={r['complete']} nodes={r['nodes']} solve_ns={solve_ns}"
                print(line, flush=True)
                log.write(line + "\n")
                log.flush()
                if not r["complete"]:
                    break

                proof = r["proof"]
                witness = {
                    "schema": "erd169.finite.v1",
                    "k": str(k),
                    "N": str(n),
                    "members": list(map(str, r["witness"])),
                    "score": proof["witness_score"],
                }
                assert st.verify_finite(witness)["valid"]
                assert v169.verify_finite(witness)["valid"]

                # Triple replay in both independent engines before advancing.
                t_rep = time.monotonic_ns()
                for _ in range(3):
                    assert st.replay(proof)["valid"]
                    assert proof_replay.replay_proof(proof, witness)["valid"]
                replay_ns = (time.monotonic_ns() - t_rep) // 3

                stem = f"c6_g{k}_{n}"
                for kind, obj in (("proof", proof), ("witness", witness)):
                    write_json(f"certificates/{stem}_{kind}.json", obj)
                prefix = {
                    "schema": "erd169.prefix_opt.v1",
                    "k": str(k),
                    "N": str(n),
                    "witness_sha256": hashlib.sha256(canonical_json_bytes(witness)).hexdigest(),
                    "proof_sha256": hashlib.sha256(canonical_json_bytes(proof)).hexdigest(),
                    "proof_format": "erd169.bnb.v1",
                    "tie_policy": "first optimum in deterministic warm-start traversal",
                }
                with st.digest_run("certificates"):
                    assert st.verify_prefix(prefix, Path("certificates"))["valid"]
                    assert v169.verify_prefix(prefix, Path("certificates"))["valid"]
                write_json(f"certificates/{stem}_prefix.json", prefix)

                table["rows"].append(
                    {
                        "N": str(n),
                        "value": witness["score"],
                        "members": witness["members"],
                        "prefix": f"{stem}_prefix.json",
                        "proof_bytes": str(len(canonical_json_bytes(proof))),
                        "nodes": str(r["nodes"]),
                        "replay_ns": str(replay_ns),
                        "solve_ns": str(solve_ns),
                    }
                )
                table["endpoint"] = str(n)
                table["target"] = "40"
                save(tables_path, tables)


def manifests() -> None:
    legacy = json.loads(Path("benchmarks/c6_legacy_bytes.json").read_text())
    for rel, digest in legacy["raw_sha256"].items():
        assert hashlib.sha256((Path("certificates") / rel).read_bytes()).hexdigest() == digest, rel
    for name, old in legacy["manifests"].items():
        p = Path("certificates") / name
        m = json.loads(p.read_text())
        assert m["certificates"][: len(old)] == old, name
        if name == "MANIFEST.json":
            existing = {e["path"] for e in m["certificates"]}
            for path in sorted(Path("certificates").glob("c6_*.json")):
                if path.name not in existing:
                    obj = st.load_strict(path)
                    m["certificates"].append(
                        {
                            "path": path.name,
                            "sha256": hashlib.sha256(canonical_json_bytes(obj)).hexdigest(),
                        }
                    )
            save(p, m)
            print(f"MANIFEST.json entries: {len(m['certificates'])}")


def timings() -> None:
    default_runs = []
    for run_idx in range(1, 4):
        t0 = time.monotonic_ns()
        proc = subprocess.run(
            [sys.executable, "-B", "verifiers/standalone_verify.py", "certificates/MANIFEST.json"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        elapsed_ns = time.monotonic_ns() - t0
        assert proc.returncode == 0, proc.stderr
        default_runs.append(
            {
                "run": run_idx,
                "elapsed_ns": str(elapsed_ns),
                "returncode": proc.returncode,
                "under_10s": elapsed_ns < 10_000_000_000,
            }
        )
        print(f"MANIFEST.json run {run_idx}: {elapsed_ns} ns")

    t0 = time.monotonic_ns()
    proc_deep = subprocess.run(
        [sys.executable, "-B", "verifiers/standalone_verify.py", "certificates/MANIFEST_DEEP.json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    deep_ns = time.monotonic_ns() - t0
    assert proc_deep.returncode == 0, proc_deep.stderr
    print(f"MANIFEST_DEEP.json run: {deep_ns} ns")

    payload = {
        "MANIFEST.json": default_runs,
        "MANIFEST_DEEP.json": {
            "elapsed_ns": str(deep_ns),
            "returncode": proc_deep.returncode,
        },
        "all_default_under_10s": all(r["under_10s"] for r in default_runs),
    }
    save("benchmarks/c6_timings.json", payload)


def reconcile() -> None:
    from submissions.build_oeis import certified_tables

    legacy = json.loads(Path("benchmarks/c6_legacy_bytes.json").read_text())
    for rel, digest in legacy["raw_sha256"].items():
        assert hashlib.sha256((Path("certificates") / rel).read_bytes()).hexdigest() == digest, rel

    tables = json.loads(Path("benchmarks/oeis_tables.json").read_text())["tables"]
    cert_tables = certified_tables()
    assert len(tables) == len(cert_tables) == 4
    for t_file, t_cert in zip(tables, cert_tables):
        assert t_file["k"] == t_cert["k"]
        assert len(t_file["rows"]) == len(t_cert["rows"])
        for r_f, r_c in zip(t_file["rows"], t_cert["rows"]):
            assert r_f["N"] == r_c["N"]
            assert r_f["value"] == r_c["value"]
            assert r_f["members"] == r_c["members"]

    m_default = json.loads(Path("certificates/MANIFEST.json").read_text())["certificates"]
    m_deep = json.loads(Path("certificates/MANIFEST_DEEP.json").read_text())["certificates"]
    assert m_default[: len(legacy["manifests"]["MANIFEST.json"])] == legacy["manifests"]["MANIFEST.json"]
    assert m_deep == legacy["manifests"]["MANIFEST_DEEP.json"]

    z125_data = json.loads(Path("benchmarks/c6_z125_measure.json").read_text())
    timings_path = Path("benchmarks/c6_timings.json")
    timings_data = json.loads(timings_path.read_text()) if timings_path.exists() else None
    c6_files = sorted(p.name for p in Path("certificates").glob("c6_*.json"))
    oeis_files = sorted(p.name for p in Path("submissions/oeis").glob("*.txt"))

    result = {
        "scope": "ERD-106 Campaign 6 local research artifact; Z/125Z Gate G1 failed (64 <= M <= 80); no release",
        "status": "CHANGES" if not Path("certificates/c6_z125_max.json").exists() else "COMPLETE",
        "legacy_files": len(legacy["raw_sha256"]),
        "new_certificates": len(c6_files),
        "manifest_entries": {
            "MANIFEST.json": len(m_default),
            "MANIFEST_DEEP.json": len(m_deep),
        },
        "prefix_endpoints": {t["k"]: int(t["endpoint"]) for t in tables},
        "prefix_rows": sum(len(t["rows"]) for t in tables),
        "oeis_file_count": len(oeis_files),
        "z125": {
            "closed": Path("certificates/c6_z125_max.json").exists(),
            "claim": z125_data["claim"],
            "gate_g1_passed": z125_data["gate_g1_passed"],
            "bounds": {"lower": 64, "upper": 80},
            "measurements": z125_data["measurements"],
        },
        "timings": timings_data,
        "default_under_10s": bool(timings_data and timings_data.get("all_default_under_10s")),
        "release": "User trial and explicit approval required; Relay cannot deploy.",
    }
    save("benchmarks/campaign6_results.json", result)
    print("Reconciled Campaign 6 results:", result["prefix_rows"], "rows;", result["manifest_entries"])


def main() -> None:
    phases = {
        "baseline": baseline,
        "z125-measure": z125_measure,
        "z125-full": z125_full,
        "prefixes": prefixes,
        "manifests": manifests,
        "reconcile": reconcile,
        "timings": timings,
    }
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=phases)
    args = parser.parse_args()
    if Path.cwd().resolve() != ROOT:
        raise ValueError("run from repository root")
    phases[args.phase]()


if __name__ == "__main__":
    main()
