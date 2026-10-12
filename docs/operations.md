# Operations and recovery

SSH to the Linux host as an authorized operator. The static dashboard cannot mutate state. Use the installed environment and `python -m app.cli status`. A publication outage leaves old website observations, so local DB status and journald are authoritative.

Commands are listed in README and `python -m app.cli --help`. Cycle commands enqueue; `worker-once` executes one queued job, and the service runs continuously. Audit records capture manual actions. Pause gates new allocation/meeting work, not exits. A missed Monday opening after the entry deadline retains cash. Unsupported exit observations keep positions open and require recovery; a new week is blocked until they reconcile.

```bash
sudo systemctl restart ai-investment-lab
sudo journalctl -u ai-investment-lab --since '1 hour ago'
python -m app.cli status
python -m app.cli retry --id '<failed-job-id>'
python -m app.cli recover-exit --date '<original-monday>' --yes
python -m app.cli publish-site --dry-run
python -m app.cli publish-site
```

Queue claiming uses row locks, lease tokens and 20-second heartbeat; an abandoned 15-minute lease is reclaimable. Trading state locks/idempotency remain the financial-effect safeguard. Never launch multiple SQLite workers. Job failures preserve safe error category and incident summary, retry with bounded backoff, then stay FAILED for operator action. Auth failures require service-account login repair; never print saved auth or database URLs into logs.

Recovery priorities: liquidation/reconciliation first; review second; meetings third; publishing last. A failed Friday review can be retried against existing reconciled outcomes without altering original fills. A failed manager meeting preserves accepted turns and frozen context; a retry resumes rather than regenerates speech. Publication retries reuse the frozen revision.

Cron changes: verify target implementation, New York timezone/DST, all three entries, service-owned lock files, and a synthetic invocation. Missing cron delivery is separate from a worker failure. The worker scans missing deliveries every minute: it enqueues a still-timely opening, records missed historical openings/meetings without invented work, and routes unresolved exits to the next supported session. A separate host monitor should alert if the worker itself is unavailable. Do not assume a stale website identifies the cause.

Settings live in protected environment configuration. Pause, edit/review settings under versioned operational change control, restart the worker and run preflight. Material risk/model changes should be audited before resuming; no browser control changes settings. Use `python -m app.cli set-setting --key max_stock_allocation --value .25 --yes` for allowlisted model, risk, cost, deadline and learning changes. Versioned database values are adopted by the worker between jobs and retained with audit records. Credentials, provider/experiment identity and hosting visibility remain protected deployment configuration.

Backup: encrypt `pg_dump -Fc`, restrict storage permissions, rotate keys, retain a tested restore procedure. Restore into an isolated DB, inspect account/ledger consistency and stage/run IDs, then switch configuration during a controlled pause. Git rollback affects displayed records only. To restore the site, rebuild known committed content with `npm ci && npm run build`; it need not contact Linux. Never use a Git rollback to reverse ledger history.
