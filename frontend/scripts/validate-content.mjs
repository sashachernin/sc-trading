import Ajv from "ajv";
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
const base = process.cwd();
const root = path.resolve(base, "..");
const read = (p) =>
  JSON.parse(fs.readFileSync(path.join(base, "public/data", p), "utf8"));
const ajv = new Ajv({ strict: false, allErrors: true });
const contracts = {};
for (const name of [
  "research",
  "decision",
  "review",
  "manifest",
  "overview",
])
  contracts[name] = ajv.compile(
    JSON.parse(
      fs.readFileSync(
        path.join(base, "lib/schemas", `${name}.v1.json`),
        "utf8",
      ),
    ),
  );
function validate(name, data) {
  if (!contracts[name](data))
    throw Error(`Contract ${name}: ${JSON.stringify(contracts[name].errors)}`);
}
const m = read("manifest.json");
validate("manifest", m);
if (m.schema_version !== "1" || m.label !== "PAPER / SIMULATED")
  throw Error("Invalid manifest");
const allowed = [
  "frontend/public/data/",
  "frontend/public/transcripts/",
  "frontend/content/meetings/",
];
for (const f of m.files) {
  if (
    !allowed.some((p) => f.path.startsWith(p)) ||
    f.path.split("/").includes("..")
  )
    throw Error("Unsafe path");
  const data = fs.readFileSync(path.join(root, f.path));
  if (
    data.length !== f.bytes ||
    crypto.createHash("sha256").update(data).digest("hex") !== f.sha256
  )
    throw Error("Hash mismatch: " + f.path);
  if (
    /<script|javascript:|github_pat_|-----BEGIN .*PRIVATE KEY|postgres(?:ql)?:\/\//i.test(
      data.toString(),
    )
  )
    throw Error("Unsafe content");
}
const o = read("overview.json");
validate("overview", o);
for (const k of ["equity", "cash", "initial_cash", "cumulative_pnl"])
  if (!/^-?\d+(\.\d+)?$/.test(o[k])) throw Error("Invalid Decimal");
if (
  (BigInt(o.equity.replace(".", "")) - 100000n).toString() !==
  BigInt(o.cumulative_pnl.replace(".", "")).toString()
)
  throw Error("Account P&L mismatch");
for (const w of read("weeks/index.json")) {
  const detail = read(`weeks/${w.id}.json`);
  if (detail.decision) validate("decision", detail.decision);
  if (detail.review) validate("review", detail.review);
  const candidateSchema = JSON.parse(
    fs.readFileSync(path.join(base, "lib/schemas/research.v1.json"), "utf8"),
  ).$defs.Candidate;
  const validateCandidate = ajv.compile(candidateSchema);
  for (const p of detail.proposals) {
    const { id, run_id, role, ...candidate } = p;
    if (!validateCandidate(candidate)) throw Error("Invalid exported proposal");
  }
  if (detail.id !== w.id || detail.label !== "PAPER / SIMULATED")
    throw Error("Invalid week route");
}
console.log(`Validated snapshot ${m.snapshot_id}: ${m.files.length} files`);
