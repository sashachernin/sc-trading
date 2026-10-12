from pathlib import Path
import json
from app.agents.contracts import CONTRACTS
from app.publishing.contracts import Manifest, AccountOverview
from app.config import ROOT

(ROOT / "frontend/lib/schemas").mkdir(parents=True, exist_ok=True)
for name, model in dict(CONTRACTS, manifest=Manifest, overview=AccountOverview).items():
    (ROOT / "schemas" / f"{name.lower()}.v1.json").write_text(
        json.dumps(model.model_json_schema(), indent=2) + "\n"
    )

    (ROOT / "frontend/lib/schemas" / f"{name.lower()}.v1.json").write_text(
        json.dumps(model.model_json_schema(), indent=2) + "\n"
    )
