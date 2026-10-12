"""Authenticated live research-only verification. No orders, ledger changes or cycle rewrites."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
from app.config import Settings
from app.services import Lab
from app.agents.contracts import Research
from app.market_data.providers import provider, screen, iso

cfg = Settings()
if cfg.codex_mode != "real" or not cfg.independent_web_research:
    raise SystemExit("Real Codex and independent web research required")
lab = Lab(cfg)
cutoff = iso(datetime.now(timezone.utc))
packet = screen(provider(cfg).packet(cfg.universe.split(","), cutoff, "entry"), cfg)
current = {
    "market": packet,
    "research_universe": cfg.universe.split(","),
    "independent_web_research": True,
    "research_only": "Off-schedule verification at this actual cutoff. Do not claim a morning run or place trades.",
}


def run(role):
    with lab.sessions() as session:
        prompt, manifest = lab.compiler.compile(
            session, role, "RESEARCH", current, Research, cutoff
        )
    output, metadata = lab.runner.run(role, "RESEARCH", prompt, Research, current)
    lab.validate_refs(output, "RESEARCH", current, role)
    return {
        "role": role,
        "output": output,
        "metadata": metadata,
        "prompt_manifest": manifest,
    }


with ThreadPoolExecutor(max_workers=2) as pool:
    records = list(pool.map(run, ["researcher_a", "researcher_b"]))
report = {
    "label": "PAPER / SIMULATED — RESEARCH-ONLY VERIFICATION",
    "cutoff": cutoff,
    "completed_at": iso(datetime.now(timezone.utc)),
    "account_mutations": False,
    "original_monday_result_preserved": True,
    "researchers": records,
}
path = (
    cfg.state_dir
    / "research-checks"
    / ("web-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
)
path.parent.mkdir(mode=0o700, exist_ok=True)
path.write_text(json.dumps(report, indent=2) + "\n")
path.chmod(0o600)
for r in records:
    print(
        r["role"],
        "web calls:",
        r["metadata"]["web_activity"]["completed_calls"],
        "sources:",
        len(r["output"]["sources"]),
        "candidates:",
        len(r["output"]["candidates"]),
    )
print("Research-only report saved:", path)
