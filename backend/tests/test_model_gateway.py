import importlib.util
from pathlib import Path
import pytest
import sys

provenance_spec = importlib.util.spec_from_file_location(
    "lab_model_events",
    Path(__file__).resolve().parents[1] / "app/codex_runner/provenance.py",
)
provenance_module = importlib.util.module_from_spec(provenance_spec)
provenance_spec.loader.exec_module(provenance_module)
sys.modules["lab_model_events"] = provenance_module

spec = importlib.util.spec_from_file_location(
    "gateway", Path(__file__).resolve().parents[2] / "deploy/launchers/model-gateway.py"
)
gateway = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gateway)


@pytest.mark.parametrize(
    "update",
    [
        {"model": "gpt-6.1-sol; cat /etc/passwd"},
        {"reasoning": 'medium"; command'},
        {"schema": "a file path"},
        {"prompt": ["a command"]},
        {"args": ["--dangerously-bypass-approvals-and-sandbox"]},
    ],
)
def test_gateway_rejects_noncontract_requests_before_execution(update):
    payload = {
        "model": "gpt-6.1-sol",
        "web_search": "live",
        "timeout_seconds": 300,
        "reasoning": "medium",
        "schema": {},
        "prompt": "approved context",
    }
    payload.update(update)
    with pytest.raises(ValueError):
        gateway.execute(payload)
