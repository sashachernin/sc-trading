from datetime import datetime, timezone
import json
from decimal import Decimal
import pytest
from pydantic import ValidationError
from app.agents.contracts import Research, ResearchSource
from app.codex_runner.provenance import web_activity, codex_output_schema
from app.codex_runner.runner import RunnerError


def source(**updates):
    return {
        "id": "web-researcher_a-1",
        "url": "https://www.sec.gov/Archives/example",
        "title": "Issuer disclosure",
        "published_at": None,
        "finding": "Reported earnings; verify exact filing.",
    } | updates


def test_actual_web_events_not_model_claims():
    raw = "\n".join(
        json.dumps(x)
        for x in [
            {
                "type": "item.completed",
                "item": {"type": "agent_message", "text": "I searched the web"},
            },
            {
                "type": "item.completed",
                "item": {
                    "type": "web_search",
                    "action": {"type": "search", "query": "Apple earnings"},
                },
            },
            {"type": "item.started", "item": {"type": "web_search"}},
        ]
    )
    activity = web_activity(raw.encode())
    assert activity["completed_calls"] == 1
    assert activity["calls"][0]["query"] == "Apple earnings"
    assert "I searched" not in json.dumps(activity)


def test_strict_cli_schema_and_legacy_records():
    schema = codex_output_schema(Research.model_json_schema())
    assert set(schema["required"]) == set(schema["properties"])
    assert "default" not in json.dumps(schema)
    old = Research(
        role="researcher_a",
        cutoff="x",
        snapshot_id="s",
        candidates=[],
        abstention_reason="No supplied data",
    )
    assert old.sources == []


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com",
        "https://localhost/x",
        "https://127.0.0.1/x",
        "https://10.0.0.1/x",
        "https://user:pass@example.com/x",
        "javascript:alert(1)",
    ],
)
def test_source_links_reject_nonpublic_and_unsafe_urls(url):
    with pytest.raises(ValidationError):
        ResearchSource(**source(url=url))


def test_independent_proposal_can_use_web_evidence_without_engine_quote(lab):
    now = datetime.now(timezone.utc).isoformat()
    lab.settings = lab.settings.model_copy(
        update={"codex_mode": "real", "independent_web_research": True}
    )
    candidate = {
        "ticker": "AAPL",
        "company": "Apple",
        "rank": 1,
        "max_allocation": ".25",
        "expected_return": 0.02,
        "downside": -0.03,
        "probability_profit": 0.55,
        "confidence": 0.5,
        "thesis": "Sourced research hypothesis",
        "catalysts": [],
        "risks": ["Uncertain earnings"],
        "invalidation": "Contradictory disclosure",
        "assumptions": ["Subjective forecast; not an executable quote"],
        "evidence_ids": ["web-researcher_a-1"],
    }
    output = Research(
        role="researcher_a",
        cutoff=now,
        snapshot_id="s",
        candidates=[candidate],
        abstention_reason=None,
        research_summary="Independently compared issuer disclosures",
        investigated_tickers=["AAPL"],
        sources=[
            source(),
            source(id="web-researcher_a-2", url="https://investor.apple.com/"),
        ],
    ).model_dump(mode="json")
    current = {"market": {"quotes": {}, "cutoff": now, "id": "s"}}
    lab.validate_refs(output, "RESEARCH", current, "researcher_a")
    output["candidates"][0]["evidence_ids"] = ["invented-evidence"]
    with pytest.raises(RunnerError):
        lab.validate_refs(output, "RESEARCH", current, "researcher_a")


def test_future_web_information_is_rejected(lab):
    lab.settings = lab.settings.model_copy(
        update={"codex_mode": "real", "independent_web_research": True}
    )
    output = {
        "role": "researcher_a",
        "cutoff": "2026-10-12T13:35:00+00:00",
        "snapshot_id": "s",
        "candidates": [],
        "abstention_reason": "Research check",
        "research_summary": "Searched disclosure",
        "investigated_tickers": ["AAPL"],
        "sources": [source(published_at="2026-10-12T14:00:00+00:00")],
    }
    with pytest.raises(RunnerError):
        lab.validate_refs(
            output,
            "RESEARCH",
            {"market": {"quotes": {}, "cutoff": output["cutoff"], "id": "s"}},
            "researcher_a",
        )
