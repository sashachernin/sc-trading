# Learning methodology

Stable base prompts define permissions and role. The analyst proposes add/replace/retire lessons, expiring hypotheses or allowlisted soft parameters. Every patch carries target, evidence, confidence, expected effect, duration, success metric, rollback condition and expiry. Code validates evidence existence, dates, parameter range, prior lesson ownership, role memory capacity and the maximum three new activations per week.

`auto_bounded` activates valid lesson/hypothesis updates for the next eligible cycle. `manual` keeps valid patches as candidates for an audited CLI approval. `shadow_then_promote` retains candidates without silently activating them. A independently tracked shadow/frozen-overlay account and automated promotion evaluation are not implemented yet; the CLI refuses to claim a shadow promotion. Soft-parameter patches enter the same labeled overlay with their allowlisted parameter/value and guide the next role's research. They never change deterministic execution limits.

```bash
python -m app.cli approve-lesson --id '<lesson-id>' --yes
python -m app.cli rollback-lesson --id '<lesson-id>' --yes
```

Manual approval supports add/hypothesis/parameter; replacements/retirements are supported by the automated gate. Rollback changes active research guidance prospectively and appends an overlay version; it does not rewrite an old prompt or reverse a trade. Expired text is omitted from future contexts.

The integration test demonstrates an accepted Friday patch in Avery's next Monday prompt with the exact overlay version, while Morgan receives only Morgan's lessons. Sunday can discuss a lesson; speech cannot activate it. Learning text is never trusted to calculate money, expand permissions or bypass risk.

Performance is exploratory. The site distinguishes paper account P&L from matched raw-price counterfactual returns and a SPY comparison. One synthetic week demonstrates control flow, not forecasting quality, calibration or strategy profitability. Patch success metrics are retained for evaluation; an automated statistically meaningful calibration/causal learning evaluator remains future work.
