import { createHash } from "node:crypto";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

const directory = "certificates";
function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  if (value !== null && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonical(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}
for (const file of readdirSync(directory).filter((name) => name.endsWith(".json") && name !== "MANIFEST.json").sort()) {
  const bytes = Buffer.from(canonical(JSON.parse(readFileSync(join(directory, file), "utf8"))));
  const digest = createHash("sha256").update(bytes).digest("hex");
  process.stdout.write(`${file} ${digest}\n`);
}
