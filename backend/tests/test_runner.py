import os, stat
import pytest
from app.codex_runner.runner import CodexRunner, RunnerError
from app.agents.contracts import Research


def executable(tmp_path, body):
    p = tmp_path / "fake-real-codex"
    p.write_text("#!/usr/bin/python3\nimport sys,os,json,time\n" + body)
    p.chmod(0o700)
    return str(p)


def test_real_argument_array_environment_and_validation(lab, tmp_path, monkeypatch):
    capture = tmp_path / "capture.json"
    body = f"""
if '--version' in sys.argv:print('test-codex 1');sys.exit()
capture={str(capture)!r}
with open(capture,'w') as f:json.dump({{'args':sys.argv,'env':dict(os.environ),'stdin':sys.stdin.read()}},f)
output=sys.argv[sys.argv.index('--output-last-message')+1]
with open(output,'w') as f:json.dump({{'role':'researcher_a','cutoff':'now','snapshot_id':'s','candidates':[],'abstention_reason':'Insufficient evidence'}},f)
"""
    cfg = lab.settings.model_copy(
        update={
            "codex_mode": "real",
            "codex_binary": executable(tmp_path, body),
            "codex_model_researcher_a": "operator-model",
            "independent_web_research": False,
        }
    )
    monkeypatch.setenv("ALPACA_SECRET_KEY", "secret-for-test")
    monkeypatch.setenv("DATABASE_URL", "private-db")
    output, meta = CodexRunner(cfg).run(
        "researcher_a", "RESEARCH", "approved prompt", Research, {}
    )
    import json

    record = json.loads(capture.read_text())
    args = record["args"]
    assert args[args.index("--sandbox") + 1] == "read-only"
    assert "--ephemeral" in args and "--ignore-user-config" in args
    assert args[args.index("--model") + 1] == "operator-model"
    assert record["stdin"] == "approved prompt"
    assert (
        "ALPACA_SECRET_KEY" not in record["env"] and "DATABASE_URL" not in record["env"]
    )
    assert meta["runner"] == "fresh-subprocess"
    assert output["candidates"] == []


@pytest.mark.parametrize(
    "body,category",
    [
        ("sys.stderr.write('authentication 401');sys.exit(1)", "AUTHENTICATION"),
        ("sys.stderr.write('429');sys.exit(1)", "RATE_LIMIT"),
        (
            "open(sys.argv[sys.argv.index('--output-last-message')+1],'w').write('{bad')",
            "VALIDATION",
        ),
        ("time.sleep(10)", "TIMEOUT"),
    ],
)
def test_runner_failure_categories(lab, tmp_path, body, category):
    cfg = lab.settings.model_copy(
        update={
            "codex_mode": "real",
            "codex_binary": executable(tmp_path, body),
            "codex_model_researcher_a": "configured",
            "runner_timeout": 1 if category == "TIMEOUT" else 10,
            "independent_web_research": False,
        }
    )
    with pytest.raises(RunnerError) as e:
        CodexRunner(cfg).run("researcher_a", "RESEARCH", "prompt", Research, {})
    assert e.value.category == category


def test_missing_model_fails_before_subprocess(lab):
    cfg = lab.settings.model_copy(
        update={"codex_mode": "real", "codex_model_researcher_a": ""}
    )
    with pytest.raises(RunnerError, match="MODEL_NOT_CONFIGURED"):
        CodexRunner(cfg).run("researcher_a", "RESEARCH", "", Research, {})
