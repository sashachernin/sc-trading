"""Check real exported routes and downloadable content without a live backend."""

import json
from pathlib import Path
from app.config import ROOT

out = ROOT / "frontend/out"
data = out / "data"
assert (out / "index.html").exists(), "Run npm run build first"
for route in ("weeks", "meetings", "learning", "operations"):
    assert (out / route / "index.html").exists(), route
for item in json.loads((data / "weeks/index.json").read_text()):
    assert (out / "weeks" / item["id"] / "index.html").exists(), item["id"]
for item in json.loads((data / "meetings/index.json").read_text()):
    assert (out / "meetings" / item["id"] / "index.html").exists(), item["id"]
    assert (out / "transcripts" / f"{item['id']}.md").exists(), item["id"]
assert (data / "performance.csv").exists()
assert "PAPER / SIMULATED" in (out / "index.html").read_text()
print("Static routes, generated articles, paper labels and downloads verified.")
