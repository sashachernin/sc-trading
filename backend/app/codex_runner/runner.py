import json, os, signal, subprocess, tempfile, time, sys
from pathlib import Path
from app.config import ROOT
from app.context.compiler import canonical


class RunnerError(RuntimeError):
    def __init__(self, category):
        super().__init__(category)
        self.category = category


class CodexRunner:
    def __init__(self, settings):
        self.settings = settings

    def run(self, role, purpose, prompt, contract, packet):
        cfg = self.settings
        model = (
            cfg.model_for(role) if cfg.codex_mode == "real" else "synthetic-fixture-v1"
        )
        if not model:
            raise RunnerError("MODEL_NOT_CONFIGURED")
        run_root = cfg.state_dir / "runs"
        run_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        with tempfile.TemporaryDirectory(prefix="run-", dir=run_root) as folder:
            workspace = Path(folder)
            workspace.chmod(0o700)
            schema = workspace / "schema.json"
            schema.write_text(canonical(contract.model_json_schema()))
            output = workspace / "final.json"
            if cfg.codex_mode == "fake":
                args = [
                    sys.executable,
                    str(ROOT / "scripts/fake_codex.py"),
                    "exec",
                    "--output-last-message",
                    str(output),
                ]
                stdin = canonical({"role": role, "purpose": purpose, "packet": packet})
            else:
                args = [
                    cfg.codex_binary,
                    "exec",
                    "--ephemeral",
                    "--ignore-user-config",
                    "--ignore-rules",
                    "--skip-git-repo-check",
                    "--sandbox",
                    "read-only",
                    "--json",
                    "--color",
                    "never",
                    "--model",
                    model,
                    "-c",
                    f'model_reasoning_effort="{cfg.codex_reasoning}"',
                    "-c",
                    'shell_environment_policy.inherit="none"',
                    "-c",
                    'web_search="disabled"',
                    "--cd",
                    str(workspace),
                    "--output-schema",
                    str(schema),
                    "--output-last-message",
                    str(output),
                    "-",
                ]
                stdin = prompt
            env = {
                k: os.environ[k]
                for k in ("PATH", "LANG", "LC_ALL", "SSL_CERT_FILE", "SSL_CERT_DIR")
                if k in os.environ
            }
            env.update(
                HOME=str(workspace),
                CODEX_HOME=cfg.codex_auth_home,
                TMPDIR=str(workspace),
            )

            start = time.monotonic()
            with (
                (workspace / "events").open("wb") as events,
                (workspace / "errors").open("wb") as errors,
            ):
                proc = subprocess.Popen(
                    [
                        sys.executable,
                        str(ROOT / "scripts/limited_exec.py"),
                        str(cfg.max_output_bytes),
                        *args,
                    ],
                    stdin=subprocess.PIPE,
                    stdout=events,
                    stderr=errors,
                    env=env,
                    shell=False,
                    start_new_session=True,
                    cwd=workspace,
                )
                try:
                    proc.communicate(stdin.encode(), timeout=cfg.runner_timeout)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
                    raise RunnerError("TIMEOUT")
            if proc.returncode:
                error = (
                    (workspace / "errors").read_text(errors="replace")[:4096].lower()
                )
                if error.strip().upper() in {
                    "AUTHENTICATION",
                    "RATE_LIMIT",
                    "MODEL_UNAVAILABLE",
                    "TIMEOUT",
                    "PROCESS",
                }:
                    raise RunnerError(error.strip().upper())
                category = (
                    "AUTHENTICATION"
                    if any(
                        s in error
                        for s in ("unauthorized", "login", "authentication", "401")
                    )
                    else "RATE_LIMIT"
                    if "429" in error
                    else "MODEL_UNAVAILABLE"
                    if "model" in error
                    and any(
                        x in error
                        for x in ("not found", "unavailable", "not supported")
                    )
                    else "PROCESS"
                )
                raise RunnerError(category)
            if not output.exists():
                raise RunnerError("MISSING_OUTPUT")
            if output.stat().st_size > cfg.max_output_bytes:
                raise RunnerError("OUTPUT_TOO_LARGE")
            try:
                result = contract.model_validate_json(output.read_bytes())
            except Exception as exc:
                raise RunnerError("VALIDATION") from exc
            return result.model_dump(mode="json"), {
                "model": model,
                "reasoning": cfg.codex_reasoning,
                "duration_seconds": round(time.monotonic() - start, 3),
                "exit_code": proc.returncode,
                "runner": "fresh-subprocess",
                "codex_version": "fake-v1"
                if cfg.codex_mode == "fake"
                else subprocess.check_output(
                    [cfg.codex_binary, "--version"], env=env, text=True, timeout=10
                ).strip(),
                "usage": None,
                "usage_status": "unavailable",
            }
