import { spawnSync } from "node:child_process";

const result = spawnSync("python3", [
  "-B",
  "solvers/gk_bnb.py",
  "--k", "3",
  "--N", "24",
  "--max-nodes", "2000000",
  "--max-seconds", "60",
], { encoding: "utf8", timeout: 75000 });
if (result.error) throw result.error;
if (result.status !== 0) {
  process.stderr.write(result.stdout + result.stderr);
  process.exit(result.status ?? 1);
}
const payload = JSON.parse(result.stdout);
process.stdout.write(JSON.stringify({
  complete: payload.complete,
  nodes: payload.nodes,
  witness: payload.witness,
  score: payload.score,
  seconds: payload.seconds,
}, null, 2) + "\n");
