"""Allowlisted evidence of actual Codex web-tool activity, never raw model logs."""

import hashlib
import json


def codex_output_schema(schema):
    """Codex strict outputs require every property; legacy records retain defaults."""
    if isinstance(schema, list):
        return [codex_output_schema(value) for value in schema]
    if not isinstance(schema, dict):
        return schema
    result = {
        key: codex_output_schema(value)
        for key, value in schema.items()
        if key != "default"
    }
    if "properties" in result:
        result["required"] = list(result["properties"])
    return result


def web_activity(raw):
    calls = []
    for line in raw.splitlines():
        try:
            event = json.loads(line)
        except (ValueError, TypeError):
            continue
        if event.get("type") == "lab.web_activity":
            return event["data"]  # Trusted local gateway emits this envelope.
        item = event.get("item", {})
        if event.get("type") != "item.completed" or item.get("type") != "web_search":
            continue
        action = item.get("action") or {}
        record = {"type": str(action.get("type", "search"))[:30]}
        for name in ("query", "url", "pattern"):
            if isinstance(action.get(name), str):
                record[name] = action[name][:2000]
        if isinstance(action.get("queries"), list):
            record["queries"] = [str(q)[:300] for q in action["queries"][:12]]
        calls.append(record)
    return {
        "completed_calls": len(calls),
        "calls": calls[:50],
        "event_stream_sha256": hashlib.sha256(raw).hexdigest(),
        "verification": "observed Codex item.completed web_search events; source claims are model reports",
    }
