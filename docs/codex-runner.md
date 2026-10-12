# Codex runner

Installed CLI inspected during implementation: **codex-cli 0.162.1**. `codex exec --help` confirmed `--ephemeral`, `--ignore-user-config`, `--ignore-rules`, `--sandbox read-only`, `--json`, `--output-schema`, `--output-last-message`, `--skip-git-repo-check`, stdin prompts and role-specific `--model`.

The runner launches an argument array with `shell=False`, a fresh private directory, minimal environment, separate process group, protected schema/output paths, hard timeout and OS file-size cap. Events and errors remain outside the published view; only sanitized metadata is persisted. Timeout kills the whole group. Authentication, rate limits, timeout, process and validation failures are distinct categories. Transient errors have bounded retries. Model IDs are required in real mode and never silently replaced.

```bash
# As the execution service identity; install the official CLI per current docs.
codex --version
codex login
codex exec --help
# Configure CODEX_AUTH_HOME to the execution identity's protected auth directory.
/opt/ai-investment-lab/.venv/bin/python -m app.cli preflight
```

Official CLI reference: https://developers.openai.com/codex/cli/reference . Verify supported flags on upgrades. Preflight checks executable/version and configured settings; an authenticated schema-constrained invocation must be performed under the deployed identity before activation. It does not prove access to a model merely by printing its configured name.

The child receives PATH, locale/TLS settings, temporary HOME, `CODEX_HOME` for auth and its isolated TMPDIR. Database/provider/Git secrets are not inherited. User configuration/rules and inherited shell environment are disabled. RESEARCH uses live hosted web search; other purposes disable browsing. Saved authentication is a secret and must be readable only by the execution identity.

**Production isolation:** the same Unix identity can still read any files it is permitted to read, even when child environment variables are absent. A Codex read-only sandbox prevents writes, not disclosure of arbitrary readable application secrets. Use a distinct execution Unix identity and an audited launcher (e.g. a narrowly configured sudo/systemd sandbox) that only accepts a workspace below the private runs root, has no access to `/etc/ai-investment-lab`, database files or publishing checkout/credentials, and receives only auth plus approved context. Configure `CODEX_BINARY` to that launcher. Do not enable unattended real runs until this boundary has been verified. The supplied service hardens the worker but is not a substitute for separate model-process filesystem isolation.

The synthetic executable `scripts/fake_codex.py` returns contract-valid fixtures, with different role speech and references to prior accepted turns. Synthetic outputs are prominently labeled; they are not claimed to be actual model generations. Raw token usage is unavailable in this initial runner and recorded as such, never debited from paper-account P&L.

## Installed server gateway

The current server uses `deploy/launchers/model-client.py` as CODEX_BINARY and a separate unprivileged `model-gateway.py` systemd service. It verifies SO_PEERCRED, accepts only bounded model/reasoning/schema/prompt/web mode/timeout input fields, builds the exact fresh Codex invocation, and returns JSON/category-only errors over a group-restricted local socket. The gateway filesystem hides backend and publisher paths and mounts the existing Codex login separately. Both services use NoNewPrivileges=true. Authenticated gpt-6.1-sol and namespace access tests passed. See server-operation.md for paths and status commands.

Independent researchers now use live web search with source-linked outputs and observed web-tool provenance. Research has a separate 300-second bound; no backend credential or filesystem permissions are relaxed. See independent-research.md.
