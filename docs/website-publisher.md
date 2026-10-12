# Website Publisher

PostgreSQL is authoritative. Generated website files are replaceable sanitized views. Export reads a single revision in a consistent transaction (PostgreSQL repeatable read), freezes creation time and files, and validates exact Decimal values, record IDs, file size/path caps, secret filtering and canonical transcript equality. Retrying an unchanged revision reuses its snapshot ID/time and files.

Allowed paths:

- `frontend/public/data/`: manifest, overview, week indexes/details, lessons, meeting indexes/details, operations and paper CSV.
- `frontend/public/transcripts/`: canonical Markdown downloads.
- `frontend/content/meetings/`: the same Markdown as content, never executable source.

The manifest includes source revision, schema version, source/valuation/export timestamps, expected next publication, relative paths, hashes and byte sizes. Its own hash is excluded. Source code, raw provider feeds, DB backups, Codex auth, Git credentials, diagnostic errors and complete private prompts are not exported. Frontend validation checks every hash and all generated routes before building. Sanitization uses a narrow presentation view and rejection of known secret/executable patterns; licensed content must be reviewed upstream, rather than relying on a regex as a complete DLP system.

A dedicated clean publisher checkout must be on the configured branch. It fetches/fast-forwards, applies only allowlisted paths, validates staged paths, runs `npm ci` and the locked static build, creates one coherent commit containing snapshot ID and pushes normally. Never force-push or disable repository protections. Rejected concurrent pushes reset only the known unpublished publisher commit, fast-forward and reapply with at most three attempts. Ambiguous developer changes are refused. A newer remote revision supersedes an older export; unchanged data makes no new content commit.

Local validated state, committed Git state, PUSHED_UNVERIFIED and DEPLOYED are distinct. An optional deployed-manifest check only marks DEPLOYED on exact snapshot ID; protected automation requires an operator-provided access mechanism. Without a successful verification, delivery remains PUSHED_UNVERIFIED. A private policy blocks push until operator verification. Exporting locally is always possible with `--dry-run`.

Use a separate publishing credential/identity with repository contents write access only. Prefer a Git credential helper or audited GitHub App; no embedded token URLs or tokens in model environments. Configure author compatibility with Vercel membership/automation rules. Rotate/revoke credentials independently of Codex/provider secrets; test renewal with a synthetic content push. The initial worker invokes publishing in the same process; production must separate publishing credential access from model execution using an isolated launcher/identity.

The Operations view shows previously recorded delivery to avoid recursive commits announcing the current deployment. Publication failure leaves the last website intact. Source rollback changes displayed views only, never DB account history or lessons. Git remembers older generated content: redact before committing, protect old deployment URLs and protect backups.
