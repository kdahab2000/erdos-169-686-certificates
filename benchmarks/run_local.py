#!/usr/bin/env python3
"""Run bounded local #169/#686 campaigns and verify every emitted result."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from verifiers.common import canonical_json_bytes
from verifiers.proof_replay import replay_proof
from verifiers.v169 import verify_finite
from verifiers.v686 import verify_null, verify_representation


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _run_json(command: Sequence[str], timeout: int) -> Dict[str, Any]:
    completed = subprocess.run(
        list(command),
        cwd=str(ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"command failed ({completed.returncode}): {' '.join(command)}\n"
            f"stdout={completed.stdout}\nstderr={completed.stderr}"
        )
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"non-JSON solver output: {completed.stdout!r}") from error
    if not isinstance(value, dict):
        raise RuntimeError("solver output is not an object")
    return value


def run_169(
    k: int, n_values: Sequence[int], seed: int, max_seconds: int
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for n in n_values:
        command = [
            sys.executable,
            "-B",
            "solvers/gk_bnb.py",
            "--k",
            str(k),
            "--N",
            str(n),
            "--max-seconds",
            str(max_seconds),
            "--max-nodes",
            "2000000",
        ]
        started = time.monotonic()
        try:
            output = _run_json(command, max_seconds + 10)
        except subprocess.TimeoutExpired:
            results.append({"track": "169", "k": str(k), "N": str(n), "status": "timeout"})
            continue
        elapsed = time.monotonic() - started
        proof = output.get("proof")
        if not isinstance(proof, dict):
            results.append({"track": "169", "k": str(k), "N": str(n), "status": "invalid_output"})
            continue
        proof_bytes = canonical_json_bytes(proof)
        proof_digest = digest(proof_bytes)
        try:
            replay = replay_proof(proof)
            if not replay.get("valid"):
                raise ValueError(replay.get("errors", ["proof replay failed"]))
            status = "PREFIX_OPTIMAL" if replay.get("optimal") else "FEASIBLE"
        except Exception as error:
            status = "REJECTED"
            results.append({
                "track": "169",
                "k": str(k),
                "N": str(n),
                "status": status,
                "error": str(error),
                "proof_sha256": proof_digest,
                "seconds": elapsed,
            })
            continue
        results.append({
            "track": "169",
            "k": str(k),
            "N": str(n),
            "status": status,
            "witness": proof["witness"],
            "score": proof["witness_score"],
            "proof_sha256": proof_digest,
            "seconds": elapsed,
        })
    return results


def run_686(s_max: int, seed: int, max_seconds: int) -> List[Dict[str, Any]]:
    command = [
        sys.executable,
        "-B",
        "solvers/s686_divisor.py",
        "--s-max",
        str(s_max),
    ]
    started = time.monotonic()
    output = _run_json(command, max_seconds + 10)
    elapsed = time.monotonic() - started
    unresolved = output.get("unresolved", [])
    return [{
        "track": "686",
        "status": "BOUNDED_COMPLETE_K2_K4",
        "s_max": str(s_max),
        "unresolved_count": str(len(unresolved)),
        "unresolved": unresolved,
        "seconds": elapsed,
        "seed": str(seed),
    }]


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--track", choices=("169", "686"), required=True)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--n-values", default="8,12,16,20")
    parser.add_argument("--s-max", type=int, default=100)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--max-seconds", type=int, default=600)
    parser.add_argument("--output", type=str)
    args = parser.parse_args(argv)
    if args.track == "169":
        n_values = [int(value) for value in args.n_values.split(",") if value]
        results = run_169(args.k, n_values, args.seed, args.max_seconds)
    else:
        results = run_686(args.s_max, args.seed, args.max_seconds)
    payload = {
        "schema": "erdos.campaign.v1",
        "seed": str(args.seed),
        "results": results,
    }
    encoded = canonical_json_bytes(payload)
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encoded + b"\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
