# Independent Codex web research

The isolated Codex installation includes both the CLI and its required `codex-code-mode-host` companion executable. Both researcher roles run in separate fresh GPT-6.1-Sol processes and perform their own live searches and page opens. They do not receive one another's findings. Avery investigates issuer disclosures, fundamentals and catalysts; Morgan investigates public price/volume evidence, relative strength and momentum. They compare the configured common-stock universe and may propose up to three stocks each or abstain with researched reasons.

`INDEPENDENT_WEB_RESEARCH=true` enables `web_search="live"` only for RESEARCH invocations. `RESEARCH_TIMEOUT=300` bounds each run; the isolated gateway supports at most two concurrent model processes. Hosted search works with the read-only local sandbox; shell networking and backend credentials are not opened to the agent. [Official Codex web-search documentation](https://developers.openai.com/codex/web-search).

The output includes a research summary, stocks investigated and source records with role-scoped IDs, public HTTPS URL, title, known publication timestamp (or null) and paraphrased findings. Candidate claims reference these source IDs. Known information published after the frozen research cutoff is rejected; unknown dates must be acknowledged. URLs and source assertions are model-reported evidence, not a guarantee that every fact or publication date was independently verified.

Application metadata separately records completed `web_search` tool events and bounded queries/page URLs. A real research run with zero observed web calls fails as WEB_RESEARCH_NOT_PERFORMED. Claims such as “I searched” in final prose cannot satisfy this check. Raw logs and credentials are not published.

Research can proceed when the supplied price packet is empty. A proposal must still be for a configured common stock, and deterministic application code obtains fresh supported execution observations and validates liquidity, history, security eligibility, allocation and cash before a paper purchase. Web pages never substitute for execution prices. Both accepted research reports, sources and abstentions are passed to the manager; an empty proposals list is distinguishable from missing researcher participation. Manager/analyst/meeting invocations currently use supplied records rather than new browsing.

The engine records the actual cutoff and run completion time. Later verification is not relabeled as Monday morning research. The original October 12 HOLD_CASH result remains unchanged. No late purchase or backdated rerun is performed by the research-only verification script.

```bash
sudo -u aiinvest bash -c 'set -a; source /etc/ai-investment-lab/engine.env; set +a; cd /opt/ai-investment-lab; .venv/bin/python scripts/verify-independent-research.py'
```

This invokes both researchers through the deployed gateway, validates their contracts/references and saves a private report under `state/research-checks/`. It never places orders, creates proposals in the account workflow, updates the ledger or replaces cycle history. Publication of a sanitized verification report is a separate operator action.

Compatibility: original stored researcher records retain defaults for newly added fields. The CLI receives a normalized strict JSON Schema with every property required; new model responses must supply the research fields. Synthetic fixture runs continue using supplied synthetic data without web access.

## One-time replacement on 2026-10-12

The user explicitly authorized replacing the failed morning opening once. `scripts/replace-failed-monday-once.py` runs fresh independent research and a manager decision for the existing forward cycle, using the actual later cutoff. This is an audited exception to the Monday 11:00 New York deadline, bounded to the same Monday before 15:45; normal scheduled openings retain their deadline.

The replacement requires a previously finished cash-only opening, no positions or proposals, and no prior replacement. Original agent runs remain intact; the original snapshot is archived as `entry-original`, and the original decision and stage timestamps are preserved in the operator audit and cycle data. New run IDs contain `:replacement:`. A durable marker prevents repeating the override even if research or execution fails. Current executable-price, calendar, cash and allocation checks still apply. The script is restricted to experiment `paper-2026-10-12`; it does not alter future schedules.
