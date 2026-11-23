import test from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");

function runPython(args, timeout = 120000) {
  return spawnSync("python3", ["-B", ...args], {
    cwd: root,
    encoding: "utf8",
    timeout,
  });
}

test("Python sources compile", () => {
  const result = runPython([
    "-c",
    "from pathlib import Path; [compile(p.read_text(encoding='utf-8'), str(p), 'exec') for directory in ('verifiers','solvers','evolutionary','benchmarks','tests') for p in Path(directory).glob('*.py')]",
  ]);
  assert.equal(result.status, 0, result.stdout + result.stderr);
});

test("stdlib unittest suite passes", () => {
  const result = runPython([
    "-m",
    "unittest",
    "discover",
    "-s",
    "tests",
    "-p",
    "test_*.py",
    "-v",
  ]);
  assert.equal(result.status, 0, result.stdout + result.stderr);
});

test("certificate manifest verifies standalone", () => {
  const result = runPython([
    "verifiers/standalone_verify.py",
    "certificates/MANIFEST.json",
  ]);
  assert.equal(result.status, 0, result.stdout + result.stderr);
});
