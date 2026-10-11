# Build AI Investment Lab

Build a complete, working application for a year-long, autonomous AI stock-trading research experiment. Deliver the source code, tests, database migrations, deployment files, and documentation described below.

The application has four research AI agents, a simulated investment account, an automated Website Publisher, and a read-only static website. The website shows proposals, decisions, trades, results, reviews, bounded learning updates, and a Sunday team discussion presented as a blog post. Host source code and generated website content in GitHub and connect that repository to Vercel. Linux runs the experiment and publishes versioned data; Vercel builds and serves the website from the committed files. Configure access explicitly, retaining private access by default.

## 1. Product goal

Start one paper account with exactly **$1,000 USD**. Carry its profits and losses forward throughout the experiment. The research target is **$100 in net monthly paper profit by month 12**. Present that target as an experimental objective, with actual results and uncertainty visible beside it.

Run the experiment for 12 calendar months from its configured start date. Track completed and skipped weekly cycles separately.

The weekly workflow is:

1. **Monday:** Two independent investing agents research stocks and submit proposals. A manager agent evaluates them and chooses the investments. Application code validates the decision and executes the paper purchases.
2. **Friday:** Application code sells the positions and calculates results. An analyst agent studies the week's proposals, decisions, and outcomes, then produces a review and improvements for subsequent weeks.
3. **Sunday:** The same four agents hold a manager-led team meeting about the preceding week, expectations for the coming week, lessons, questions, and issues. Publish their actual generated dialogue as a blog-style post in the dashboard.

Use a fully simulated, cash-funded, long-only account holding eligible US-listed common stocks and cash. Support fractional shares. Every account, order, position, performance chart, and export must clearly identify its results as **PAPER / SIMULATED**.

The dashboard must answer these questions:

- How much has the account gained or lost, including this month and since inception?
- What did each investing agent recommend, and what evidence did it use?
- What did the manager choose, reject, and allocate?
- What actually happened to the selected and rejected stocks?
- What did the analyst conclude, and how will those conclusions affect later runs?
- What did the team discuss on Sunday, where did they agree or disagree, and what questions are they taking into the coming week?
- When was this snapshot generated, which observations does it contain, and how fresh are its prices and results?

## 2. Architecture and deployment

Implement a GitHub monorepo using this architecture:

| Component | Implementation | Deployment |
|---|---|---|
| Website | Next.js App Router with `output: 'export'`, React, TypeScript, Tailwind CSS, accessible components | Static assets on Vercel |
| Research engine | Python 3.12+, Pydantic, application services and an operator CLI | Native remote Linux installation |
| Persistence | PostgreSQL, SQLAlchemy, Alembic | Linux or configured managed PostgreSQL |
| Background execution | Python worker with a durable PostgreSQL job queue | Linux, supervised by systemd |
| Weekly triggers | Three Linux cron entries | Monday opening, Friday closing/review, Sunday meeting |
| AI execution | Fresh non-interactive Codex CLI subprocess per agent invocation | Linux |
| Trading | Deterministic paper-execution engine and ledger | Linux |
| Website Publisher | Deterministic export, validation, Git commit and push | Linux, as a workflow stage/job |
| Version control | Frontend source, engine source, schemas, and curated generated website content | Private GitHub repository by default |
| Delivery | Vercel GitHub integration building the selected production branch | Vercel |

Use this one-way data path:

```text
Linux research engine -> PostgreSQL
                            |
                            v
                Website Publisher on Linux
                            |
               validated JSON / Markdown
                            |
                      Git commit + push
                            |
                      GitHub repository
                            |
                  Vercel static build
                            |
                 Read-only website visitors
```

Install the engine natively in a Python virtual environment. Keep agent execution, credentials, accounting, market-data access, settings changes, and job execution on Linux. Serve the website entirely from the exported Vercel deployment. The browser reads the deployed snapshot; operator commands run through authenticated SSH on Linux.

Vercel's Git integration can deploy changes pushed to the configured production branch [R1]. Next.js static export produces HTML, CSS, and JavaScript assets at build time [R2]. Configure the Vercel project root as `frontend/`, with the static export output generated by the locked Next.js build. Generate every weekly and meeting article route at build time from committed content.

Use a layout similar to:

```text
frontend/
  app/
    meetings/[slug]/
    weeks/[weekId]/
  components/
  lib/                       # Typed loaders, schemas, formatting
  content/meetings/           # Generated Markdown; data, not executable code
  public/
    data/
      manifest.json
      overview.json
      weeks/index.json
      weeks/<week-id>.json
      learning/index.json
      meetings/index.json
      meetings/<slug>.json
      operations.json
    transcripts/             # Generated, sanitized Markdown downloads
  next.config.ts
backend/
  app/
    cli/
    agents/
    codex_runner/
    context/
    jobs/
    learning/
    meetings/
    market_data/
    paper_trading/
    risk/
    publishing/
    models/
prompts/
  researcher_fundamental/
  researcher_momentum/
  manager/
  analyst/
  meeting/
deploy/
  systemd/
  cron/
schemas/                     # Versioned agent and website-export contracts
scripts/
docs/
```

GitHub stores the website's source and curated published records. PostgreSQL remains the authoritative research history and ledger. Treat generated files as replaceable views of that history. Keep the installed engine checkout separate from the publisher's working checkout so data commits do not alter running application code.

Choose supported dependency versions at implementation time and commit lockfiles. Keep model IDs, provider settings, access mode, repository/branch settings, and operational limits configurable.

## 3. Four agent roles

### Investing Agent A: fundamentals and catalysts

Research company fundamentals, valuation, quality, revisions, scheduled events, and time-stamped news supplied by the application. Focus on opportunities relevant to the Monday-to-Friday holding period.

Receive a bounded, point-in-time market packet and this agent's current learning overlay. Submit up to three ranked stock proposals, or an explicit abstention when the evidence is insufficient.

### Investing Agent B: momentum and price behavior

Research price and volume history, momentum, relative strength, volatility, gap behavior, and trend stability using the supplied data.

Receive the same eligible stock universe, with a data packet emphasizing this methodology, plus this agent's current learning overlay. Submit up to three ranked proposals or an explicit abstention.

Run the two investing agents independently. Reveal their finalized proposals to the manager after both runs reach a terminal state.

### Manager Agent

Review both sets of proposals, available cash, market context, configured risk limits, and the manager's learning overlay.

Choose one or more submitted proposals, allocate part or all of the permitted investment budget, or hold cash. Explain each acceptance and rejection with concise, evidence-linked reasoning.

Return a structured decision to application code. The deterministic risk and execution services control order creation and ledger updates.

### Analyst Agent

After Friday liquidation and reconciliation, review all proposals, the manager's choices, paper fills, costs, outcomes, benchmark results, and relevant prior lessons.

Evaluate the investing agents and manager separately. Distinguish research quality, forecasting, selection, sizing, execution, market effects, and uncertainty. Produce both a readable weekly review and structured learning patches for future runs.

The analyst's output is the feedback mechanism that improves the investing agents' and manager's prompts over time.

All four existing roles also participate in Sunday meetings through a separate meeting-mode prompt and output schema. The manager chairs the conversation. Each participant keeps its role, model configuration, active learning overlay, and a consistent, configurable display name. The meeting orchestrator is application code; the participants are these same four agents.

## 4. Weekly schedule and trading workflows

Use three automatic workflow triggers. Each cron entry calls a short command that validates the invocation and enqueues an idempotent root job. The systemd worker performs that job's stages. Monday and Friday own the investment lifecycle; Sunday owns the meeting. Each workflow requests a website publication after its records reach a committed terminal state, including a skip or failure that can be reported accurately. Publication runs as a stage/job of these workflows and can be retried independently.

| Trigger | Default time | Entrypoint |
|---|---|---|
| Monday opening cycle | 09:35 America/New_York | `python -m app.jobs.run_open_cycle` |
| Friday closing and review cycle | 15:45 America/New_York | `python -m app.jobs.run_close_cycle` |
| Sunday team meeting | 12:00 America/New_York | `python -m app.jobs.run_sunday_meeting` |

The Sunday time is a configurable initial default. Generate the three cron entries for the installed Linux cron implementation. Verify its timezone behavior during setup so the schedule follows New York market time through daylight-saving changes. Store application timestamps in UTC and display the applicable market timezone in the UI.

Wrap all three entrypoints with `flock`, using service-user-owned lock files. Add database uniqueness constraints and transactional stage transitions so repeated invocations remain safe after a process exits or restarts.

### Calendar eligibility

For the initial implementation, trade weeks in which Monday and Friday are both normal, full US equity sessions. Check the exchange calendar on Monday before research begins.

When either day is a holiday, or Friday has an early close, record `SKIPPED_NONSTANDARD_WEEK`, retain cash, and display the reason. Keep these weeks in the year-long experiment's history. Hold the Sunday meeting during an active experiment even when that week was skipped; discuss the actual skip or incident and available preparation instead of trading results that do not exist.

Recheck session availability at execution time. Handle an unexpected market interruption as an explicit incident with accurate account state.

### Monday stages

1. Check that the experiment is active, the week is eligible, and prior account state is reconciled.
2. Obtain a point-in-time market snapshot and bounded candidate universe.
3. Compile fresh prompts and run both investing agents concurrently within the configured concurrency limit.
4. Validate and persist each finalized proposal set.
5. Compile the manager prompt and run a fresh manager Codex process.
6. Validate the decision and apply deterministic eligibility, cash, allocation, and price-freshness checks.
7. Execute the approved simulated purchases or record the hold-cash decision.
8. Persist the resulting positions, cash, prompts, evidence, and timeline.
9. Request a publication of the committed proposals, manager decision, fills, and updated account snapshot.

Use a configurable Monday entry deadline. Mark an uncompleted opening workflow as missed when the deadline passes. Default to retaining cash if a required researcher or manager run fails after bounded retries.

### Friday stages

1. Load this week's account state and determine which closing stages remain unfinished.
2. Liquidate open paper positions using supported market prices.
3. Reconcile cash, fills, costs, realized profit/loss, and equity.
4. Calculate comparison results for eligible proposals and the configured benchmark over matched entry and exit windows.
5. Compile a bounded analyst prompt and run a fresh analyst Codex process.
6. Validate and persist its review and learning patches.
7. Apply the learning gate and publish eligible overlay versions for subsequent cycles.
8. Mark the weekly cycle complete.
9. Request a publication of realized results, the available analyst review, and learning updates. If the review fails, export the reconciled trading results with the review marked unavailable; publish the later successful review through a new revision.

Give liquidation priority over AI work. A delayed or failed review can be retried using the already-reconciled results. Review retries preserve the original trade records.

Run investing and formal learning on Monday and Friday, and the team discussion on Sunday. Normally publish one coherent snapshot after each workflow, approximately three content deployments per week. Between publications the website shows the last published observations, with explicit valuation and snapshot timestamps. A browser reload retrieves the deployed snapshot rather than triggering market research or obtaining a new quote. An operator may explicitly refresh/export data through the Linux CLI and request another publication.

### Recovery and operational state

Persist stage progress and distinguish queued, running, completed, skipped, failed, and recovery-required states. Preserve completed stages when retrying an interrupted workflow.

Use bounded, deadline-aware retries for transient failures. Record missed triggers, stale jobs, failed liquidation, and authentication failures locally and include safe incident summaries in the next published Operations snapshot. Provide operator CLI retries with audit records. A publication outage leaves the website at its previous snapshot, so local logs and CLI status are the authoritative operational view.

Resume already-queued unfinished work after worker restart. Handle a missed opening trigger within the configured Monday entry window; otherwise record a missed week. Route a missed exit to an explicit recovery workflow using the next supported execution opportunity and label the holding period as extended.

Keep an unfilled position open in the ledger until a supported fill occurs. Block a new weekly allocation while an unresolved prior position or accounting incident requires recovery.

## 5. Sunday team meeting and blog publication

### Experience and purpose

Hold a weekly team conversation that is enjoyable to read and sounds like colleagues talking, rather than four reports pasted together. The same four agents discuss what they worked on, what surprised them, their expectations, questions, disagreements, and operational issues. The manager leads, invites responses, asks follow-up questions, and closes the meeting.

Use a friendly, professional voice with room for light humor, candid uncertainty, and respectful disagreement when supported by the record. Give each agent a recognizable perspective consistent with its investment role. Participants should answer one another and refer to earlier remarks. Keep the prose conversational: short paragraphs, first-person updates, ordinary language, and direct questions. Allow agreement when it is genuine rather than manufacturing conflict.

Ground statements in the supplied records. A participant can say "I put too much weight on that catalyst" when its recorded proposal supports that reflection; activities, research, news, trades, or mistakes mentioned as facts must have supporting records. Expectations about the coming week are tentative observations, not completed Monday recommendations. Show the feature as an **AI-generated team discussion / paper-trading research**, with actual run dates and attribution.

Meeting permissions cover reading approved experiment records and writing meeting records. Trades, financial calculations, and formal learning-overlay activation remain responsibilities of the Monday/Friday workflows. This makes the meeting an observational, conversational part of the experiment, with Monday's independent proposals still generated from their own evidence and approved overlays.

### Schedule and source context

The Sunday entrypoint enqueues `SUNDAY_MEETING` for the configured Sunday date. Use a meeting ID distinct from the trading-cycle ID and store references to the preceding Monday-Friday cycle and the upcoming cycle. Run meetings during the active experiment, including weeks with a trading skip, cash-only choice, missing review, or unresolved incident. For a first-ever meeting, use a kickoff agenda and the initial account state.

Freeze a bounded source packet at meeting start containing:

- The preceding cycle's verified status, canonical account metrics, proposals, decision, fills, and available Friday review.
- Each participant's role-specific work summary, active overlay version, and relevant measured outcomes.
- Open operational incidents and the known upcoming exchange/event calendar as of the packet cutoff.
- At most the immediately preceding meeting's short recap and outstanding discussion questions.

Preserve the actual data cutoff and freshness. Explicitly describe incomplete weeks or unavailable information. Keep later observations out of the frozen packet even if the meeting is retried after new data arrives.

### Actual multi-agent conversation

Build a small deterministic `MeetingOrchestrator` using the existing worker, Codex runner, and prompt compiler. Each accepted utterance is the final structured output of a **fresh Codex invocation of the speaking agent**. Supply that agent's identity and relevant records, the current phase, the chair's question, and the bounded conversation so far. Preserve the role's configured model and record `purpose=MEETING_TURN`.

Use this default 11-turn agenda:

| Turns | Speaker and purpose |
|---|---|
| 1 | Manager opens, gives a grounded recap, and sets a short agenda. |
| 2-4 | Investing Agent A, Investing Agent B, and Analyst each give an update: their work, outlook, and one question or issue. |
| 5-6 | Manager asks a follow-up and selects a participant; that participant answers and may respond to another agent's point. |
| 7-8 | Manager develops the discussion and invites a different participant; that participant responds. |
| 9-10 | Manager brings in the remaining participant for a final substantive exchange. |
| 11 | Manager closes with an honest recap, open questions, and a few focus areas for the coming week. |

The manager chooses the discussion questions and the order of follow-up recipients. Application code validates that the chosen speaker is an eligible participant and that each non-manager participant is invited once in the follow-up round. This gives every participant two substantive contributions while retaining a bounded meeting. Keep agenda limits configurable within hard execution and context budgets.

The manager writes its own words; each other agent writes its own response. Render the accepted utterances in order to form the transcript. Use application-supplied speaker labels and timestamps so authorship can be verified against run records.

### Turn contract and publication

Validate a separate `MeetingTurn` schema with bounded fields:

- Application-issued meeting, turn, and run references; speaker role and phase.
- `message_markdown`: the agent's actual spoken contribution.
- `reply_to_turn_ids`: earlier accepted turns the contribution addresses.
- `evidence_ids`: supplied records supporting references to work, results, and events.
- `next_speaker`: the manager's routing choice where the phase requires one; otherwise null.
- `publication`: null except for the manager's closing turn.

The closing `publication` contains a title of at most 120 characters, a standfirst of at most 280 characters, a recap of at most 200 words, up to three takeaways, up to three open questions, and up to three upcoming focus items with an owner role and supporting turn references. Focus items are discussion notes; their status and presentation distinguish them from executed work or formal strategy changes.

Build the article body deterministically from the stored turns. Display the recap separately from the full discussion. Link financial references to canonical metrics and source records, validate structured numeric claims, and keep uncertainty visible in the prose. Preserve accepted speech when updating publication metadata. The manager's closing turn supplies the editorial summary; the article renderer supplies formatting.

After completion and validation, persist the article and enqueue a Website Publisher job. Export its structured turns and metadata as JSON, render its Markdown deterministically, commit the generated content to GitHub, and let Vercel build the new archive entry and article route. The article becomes visible after the corresponding deployment succeeds. Apply the configured site-wide access policy to article pages and their downloadable source artifacts.

### Bounded discussion and memory

Use explicit initial limits for meeting runs:

- Default 11 accepted turns; target 60-150 words per turn, maximum 180 words and 1,400 characters per spoken contribution.
- Maximum 2,000 words for the accepted dialogue and 2,800 words for the full rendered article, including recap and headings.
- Maximum 12,000 estimated input tokens per turn: 2,000 for role/meeting instructions and active overlay, 5,000 for source context, 4,000 for the current meeting transcript, and 1,000 for the output contract.
- Maximum 11 successful role invocations in the default agenda, plus at most two additional transient-failure attempts across the meeting; also apply a configurable wall-clock deadline and the runner's output/process limits.
- Maximum 1,500 characters for the recap carried into a later meeting, including at most three open questions. Carry only the latest recap forward.

Use a deterministic role-specific selection of existing lessons that fits the meeting budget; retain the full overlay version and selected lesson IDs in the manifest. Enforce both byte and estimated-token limits. Include the current meeting's accepted dialogue within its transcript budget; if necessary, deterministically omit older complete turns while preserving the chair's current question and referenced turns, and record that reduction. Keep the complete accepted transcript in the database and article.

Each turn starts fresh with this compiled packet. The next meeting receives its own current records and at most the bounded previous recap. Archived posts stay available on the website, separate from the agents' active context. Monday research and Friday formal learning keep their existing input policy; meeting conversations do not become unbounded strategy memory.

### Blog-style website experience

Add **Team Meetings** to the main navigation.

At `/meetings`, show newest-first article cards with title, date, excerpt, participant labels, completion status, linked trading week, and estimated reading time. Support pagination and a clear empty state before the first meeting.

At `/meetings/[slug]`, use a comfortable article column, generous paragraph spacing, accessible headings, and readable mobile typography. Include:

- Title, standfirst, meeting date, actual generation timestamps, AI-discussion label, and participants with consistent initials or simple avatars.
- A small factual summary of the referenced paper-trading week, linked to its dashboard and Friday review.
- The complete dialogue with a clear name and role at each speaker change; group by opening, updates, discussion, and wrap-up where useful.
- The manager's recap, takeaways, upcoming focus areas, and unresolved questions.
- Previous/next meeting navigation and an authorized Markdown transcript download.
- A collapsed provenance panel for turn/run IDs, source cutoff, model versions, prompt versions, context size, and execution usage.

Make the default presentation read like an edited meeting transcript in a blog while preserving the actual accepted messages. Include sanitized provenance in the published snapshot; retain detailed job logs on Linux. Display the last published meeting state and its observation time. The full article appears after a completed publication and Vercel build. Clearly label an intentionally published partial transcript and missing participants.

### Reliability and failure handling

Use meeting states such as `PLANNED`, `QUEUED`, `RUNNING`, `CONTENT_READY`, `CONTENT_READY_PARTIAL`, `FAILED`, `MISSED`, and `PAUSED`. Track participation and source-data completeness separately. Track export, Git push, build, and website delivery in a separate publication record so ready content is distinguishable from content verified on the website.

Protect the root job and each turn with idempotency constraints and atomic commits. A restart resumes the next unfinished turn using the frozen packet and already-accepted dialogue. Retry publication independently from generating dialogue. Make manual retries auditable and preserve prior attempts.

After bounded retries, an unavailable non-manager participant can be marked unavailable using an application-generated status notice, clearly separated from agent speech. The manager can continue with available participants and produce a visibly partial article for publication. If the manager is unavailable, retain the draft and failure status for operator retry. Keep Monday's trading workflow independent of meeting and publication success.

Finish automatic retries within the configured Sunday meeting window. Record a missed meeting when that window expires. Any manually reconstructed historical meeting must use its historical cutoff and be labeled reconstructed with its actual generation time. Track real Codex usage or available estimates separately from the simulated account's profit and loss.

## 6. Codex runner

Implement a `CodexRunner` abstraction. Each invocation launches a **new local `codex exec` process** with a generated prompt and an explicit structured-output contract.

Use a dedicated Linux service account with its own persistent Codex authentication configuration. Document installation, login under that account, and a successful non-interactive preflight run. Treat saved Codex authentication as a secret.

Verify the installed CLI's supported options during implementation and record its version. Configure the runner for:

- Fresh, ephemeral sessions and a read-only workspace.
- Prompt input through stdin or an appropriately protected temporary file.
- Schema-constrained final JSON output.
- Separate handling of final output, safe JSONL status events, and sanitized errors.
- Role-specific model and reasoning settings.
- Controlled application-supplied evidence as the research input.
- A clean per-run workspace and deterministic run configuration.

Read the model IDs from settings such as `CODEX_MODEL_RESEARCHER_A`, `CODEX_MODEL_RESEARCHER_B`, `CODEX_MODEL_MANAGER`, and `CODEX_MODEL_ANALYST`. Validate availability at preflight and show configuration failures to the operator. Persist the actual model and reasoning setting for each run. Apply a fallback only when the operator has explicitly configured an ordered fallback list.

Launch subprocesses with an argument array and `shell=False`. Give each process its own process group, a hard timeout, output-size limits, and bounded transient-error retries. Terminate the entire process group on timeout.

Use isolated run directories containing only approved context and output artifacts. Supply a minimal child environment that supports Codex authentication while keeping application, database, and data-provider credentials in the backend's environment. Use the CLI's supported sandbox controls and least-privilege filesystem permissions.

For every run, retain:

- Run ID, role, invocation purpose (`RESEARCH`, `DECISION`, `REVIEW`, `MEETING_TURN`, or optional `PUBLISHER_EDITORIAL`), linked weekly cycle, meeting/turn, or export revision, and attempt number.
- Exact compiled input and its content hash.
- Base-prompt, overlay, and context-manifest versions.
- Codex version, model, reasoning setting, and sanitized invocation metadata.
- Start/end timestamps, duration, exit code, and failure category.
- Available usage metadata.
- Final validated structured response.

Expose explicit decision summaries, evidence references, and safe execution status in the UI. Limit stored event metadata to operational information appropriate for display and auditing.

Validate final output with JSON Schema and Pydantic before using it. Distinguish authentication, rate-limit, unavailable-model, timeout, process, validation, and data errors. Treat a valid abstention or hold-cash recommendation as a successful agent result.

Provide a fake Codex executable that supports deterministic automated tests and the synthetic demonstration mode, including distinct per-role meeting replies that depend on previous turns.

## 7. Agent output contracts

Create versioned JSON Schemas and matching Pydantic models. Set `additionalProperties: false` and use explicit required fields, enums, numeric bounds, and string-length limits. Assign authoritative run and record IDs in application code and validate returned references.

### Researcher response

Include:

- Run reference, role, data cutoff, and universe snapshot reference.
- Zero to three ranked candidates; require an abstention reason when the list is empty.
- For each candidate: ticker, company, rank, maximum recommended allocation, expected holding-period return, downside case, probability of profit, and confidence.
- Concise thesis, catalysts, risks, invalidation conditions, assumptions, and supplied evidence IDs.

Define returns and probabilities consistently: document their units, admissible ranges, and holding period.

### Manager response

Include reviewed proposal IDs, approved and rejected proposals, dollar and percentage allocations, retained cash, concise decision rationales, risk considerations, uncertainty, and an explicit hold-cash outcome where applicable.

Validate proposal membership and the allocation arithmetic in application code. Record risk-engine rejections separately from manager rejections.

### Analyst response

Include a weekly summary, researcher and manager scorecards, forecast-versus-outcome comparisons, selected-versus-rejected proposal analysis, execution effects, error categories, successes, weaknesses, sample-size limitations, and structured learning patches.

Request concise explanations and evidence references sufficient to audit each conclusion.

### Meeting response

Use a separate meeting-turn contract for conversational output. Include the run/meeting/turn references, speaker, phase, `message_markdown`, `reply_to_turn_ids`, and supplied `evidence_ids`. Chair turns also return a validated `next_speaker` where appropriate; the closing turn includes the publication metadata defined in the Sunday meeting specification. Render the conversational text on the blog page and keep its JSON structure in the audit view.

## 8. Bounded context and persistent memory

Use PostgreSQL as durable research history and a deterministic `PromptCompiler` to select bounded input for each fresh Codex run.

Compose prompts from separately versioned sections:

1. Role definition and experiment rules.
2. Active learning overlay for the target agent.
3. Current point-in-time data, proposals, or completed-week results appropriate to the role.
4. Selected recent summaries.
5. Older aggregate statistics.
6. Output instructions and schema.

Use the following configurable initial input budgets:

| Section | Maximum estimated tokens |
|---|---:|
| Role definition and experiment rules | 4,000 |
| Active learning overlay | 4,000 |
| Current data and role-specific input | 14,000 |
| Recent detailed history | 5,000 |
| Older aggregate history | 3,000 |
| Output contract | 2,000 |
| **Total** | **32,000** |

Enforce the total and section budgets before execution. Add byte, character, output-size, and runtime caps. Use a model-appropriate tokenizer where available and a conservative estimator otherwise; record which method was used.

Select lower-priority context deterministically when reducing a packet. Preserve mandatory rules and schema, and fail visibly when required content alone exceeds the budget.

Include at most eight recent weekly summaries. Represent older experience using bounded aggregate statistics and active lessons. Store full historical prompts, reports, market snapshots, and meeting transcripts on Linux for audit. Export only the explicit, sanitized subset approved for website viewing.

Meeting turns use a smaller role-specific budget defined in the Sunday meeting specification. Carry forward at most the latest bounded meeting recap into the next meeting; the transcript archive remains website history. Monday research continues to use independent evidence packets and the approved learning overlays.

### Memory items

Represent each lesson as a structured record with:

- Stable ID, target agent, category, bounded text, and version.
- Evidence references, confidence, creation week, and last-confirmed week.
- Expiry or time-to-live.
- Candidate, active, expired, rejected, or rolled-back status.

Default to at most **12 active lessons per agent**, each at most **700 characters**. Manage capacity by merging, replacing, retiring, or deferring lessons. Expire weakly supported rules unless new evidence justifies renewal.

Persist a context manifest for every run listing included record IDs, prompt versions, lessons, cutoff, estimated size, and any context reduction. Show the manifest and a sanitized compiled-prompt view in the dashboard.

## 9. Learning and prompt updates

Implement learning as **stable base prompts plus bounded, versioned learning overlays**.

Keep base role definitions, accounting rules, permissions, and trading constraints in version-controlled application files. Let the analyst propose changes to a restricted overlay for either investing agent or the manager.

A learning patch supports one of these operations:

- Add, replace, or retire a lesson.
- Adjust an allowlisted soft strategy parameter within configured bounds.
- Introduce a time-limited hypothesis to test.

Require target agent, operation, referenced lesson where applicable, proposed change, evidence IDs, confidence, expected effect, test duration, success metric, rollback condition, and expiry.

### Validation and activation

Validate patches with application code. Check role eligibility, operation, parameter bounds, evidence existence, length, count, expiry, and compatibility with the fixed experiment contract. Treat lesson text as research guidance with restricted authority; enforce execution permissions and financial constraints in code regardless of its wording.

Support:

| Mode | Behavior |
|---|---|
| `auto_bounded` | Automatically activate valid patches for the next eligible cycle. Default. |
| `manual` | Require operator approval of valid patches through the Linux CLI. |
| `shadow_then_promote` | Evaluate a candidate overlay in a separately tracked comparison before promotion. |

Allow at most **three newly activated patches across all target agents per week**. Prefer expiring hypotheses when evidence is limited. Store every validation outcome, activation, replacement, expiry, and rollback.

The prompt compiler must include the active overlay in a clearly labeled section:

```text
ACTIVE LEARNING OVERLAY
Apply these versioned research lessons alongside the fixed role contract and
current evidence. Treat confidence and expiry as part of each lesson.

[Active lessons for this agent]
```

This is the mechanism by which Friday's conclusions influence the next Monday's research and manager decision. Sunday participants can discuss those published lessons and challenge them conversationally. Formal overlay changes remain governed by the analyst review and learning gate; meeting remarks and chair follow-ups are discussion records rather than automatically activated instructions.

Record the exact overlay version used in each run. Display diffs, supporting evidence, memory-cap usage, test results, and rollback history.

### Evaluating learning

Calculate exploratory forecast error, calibration, risk, net performance, and patch-specific success metrics for subsequent observations. Clearly separate hypotheses, observed associations, and well-supported findings.

Provide cash and matched-window market benchmarks. Support a fixed, frozen-overlay comparison to help evaluate the learning mechanism; keep its hypothetical account, prompts, and results separate from the primary account. Run any configured comparison as part of the same weekly workflows.

Label paper counterfactuals and historical replays as hypothetical. Show sample sizes and limitations, including regime changes, selection effects, and possible historical-model hindsight.

## 10. Market data and evidence

Implement configurable provider interfaces for symbol metadata, historical OHLCV, quotes, corporate actions, earnings/events, time-stamped news where available, market calendars, and benchmark data.

Deliver one real market-data adapter and one deterministic synthetic adapter. Document the real adapter's required credentials, coverage, freshness, licensing assumptions, and unavailable fields. Keep synthetic demonstrations in separately labeled experiments.

### Candidate screening

Create a deterministic, versioned screen over the eligible US common-stock universe. Use configurable price, liquidity, history, security-status, and quote-freshness criteria. Suggested initial minimum share price: $5.

Bound the candidate packet before sending it to either investing agent. Preserve the eligibility snapshot and screening configuration. Build role-specific packets from the same eligible universe.

### Point-in-time integrity

Record provider, observation time, publication time where available, retrieval time, cutoff, and content hash. Restrict decision inputs to evidence available at the applicable cutoff. Give supplied evidence stable IDs and validate references in every agent output.

Represent unavailable, delayed, or incomplete fields explicitly. Keep simulation-ready quote/bar data separate from adjusted series used for research. Align corporate-action treatment across prices, quantities, cash, and performance.

Keep portfolio holdings limited to eligible common stocks. A broad-market index or ETF may be used as a separately labeled comparison series.

## 11. Paper execution, accounting, and metrics

Implement the ledger and all financial calculations in deterministic application code using `Decimal` with documented precision and rounding.

Use these configurable initial limits:

- Initial cash: **$1,000.00**.
- Cash-funded long positions, with nonnegative cash after costs.
- Fractional quantities enabled.
- Maximum allocation to one stock: **40%**.
- Maximum deployed capital: **95%**.
- Cash retention: any amount up to **100%**.

Make portfolio concentration a combined ticker-level check when both agents recommend the same stock. Validate liquidity, eligibility, price freshness, quantity precision, and available funds at execution time.

### Fills and corporate actions

Use the first supported executable observation after order creation, applying a documented spread, slippage, and fee model. Record the decision time, order time, observation time, fill time, provider, and fill-model version.

Support delayed data honestly by labeling its delay and simulation assumptions. Keep fills dependent on available evidence. Represent missing quotes, partial fills, halts, splits, symbol changes, delistings, and unsuccessful exits as explicit state transitions and incidents.

Use immutable ledger entries and auditable reversal or correction records. Reconcile cash, quantities, costs, and account equity after execution and before analyst review.

### Performance

Calculate starting/current equity, cash, invested value, realized/unrealized P&L, cumulative return, weekly return, calendar-month P&L, rolling-four-week P&L, exposure, turnover, costs, drawdown, win rate, average win/loss, and profit factor where defined.

Mark valuations with timestamps and freshness. Label drawdown according to the sampling frequency used. Show undefined or statistically weak metrics explicitly rather than presenting misleading precision.

Measure forecasts over documented entry/exit windows. Calculate feasible rejected-proposal counterfactuals with the same fill assumptions and comparable sizing. Display calibration, forecast error, selection regret, risk, and prompt-version performance with sample sizes.

Track progress toward $100 monthly paper profit using net trading results. Show AI/data operating costs separately when available, distinguishing observed costs from estimates and paper P&L from research expenses.

## 12. Dashboard

Build a polished, responsive, read-only static dashboard with consistent status indicators, loading/empty/error states, accessible interactions, and a persistent **PAPER / SIMULATED** label. Add a visible snapshot ID, last-updated timestamp, valuation timestamp, and stale-data notice. Every displayed fact comes from the same validated publication revision. Configure access using the hosting-level policy described below.

### Overview

Show starting capital, equity as of the published valuation, realized/unrealized and cumulative P&L, cash, invested value, monthly and rolling-four-week profit, month-12 target progress, equity and drawdown charts, weekly returns, benchmarks, positions, fills, valuation freshness, last observed workflow stage, and the planned weekly schedule. Include a latest-meeting card linking to the Sunday post. Distinguish planned actions from confirmed completed work.

### Investing agents

Display the two agents side by side with ranked proposals, forecasts, confidence, downside cases, evidence, catalysts, risks, assumptions, submission times, and selected/rejected status. Show the model, base-prompt version, overlay version, cutoff, and context manifest for each run.

### Manager decision

Show the comparison of proposals, approved and rejected choices, retained cash, allocation, explicit rationale, uncertainty, risk-engine checks, order status, and fill details.

### Analyst review

Show the weekly narrative, individual agent scorecards, manager scorecard, forecast comparisons, accepted/rejected outcomes, execution effects, identified mistakes, successes, evidence, sample size, and proposed improvements.

### Learning journal

Show proposed and active patches, validation results, activation mode, target agent, prompt-overlay diffs, supporting weeks, test metrics, expiry, rollback history, and active memory size. Approval and rollback commands are Linux operator actions; the website displays their committed results.

### Team meetings

Provide a blog-style meeting archive at `/meetings` and an article page at `/meetings/[slug]`. Show the actual attributed discussion, manager recap, takeaways, open questions, and links to the relevant trading week and Friday review. Use the presentation and publication requirements in the Sunday meeting specification.

### Experiment history

Provide searchable published weekly cycles, proposals, decisions, orders/fills, reviews, meetings and their turns, sanitized prompt versions/manifests, model settings, and safe incident summaries. Implement search, filtering, sorting, and chart interaction locally over static data. Include a chronological weekly timeline and sanitized CSV/JSON downloads subject to the same hosting access policy.

### Operations and configuration snapshot

Show the last observed worker status, queue summary, Monday/Friday/Sunday invocations, model configuration, data freshness, and safe incident summaries. Include meeting completion/participation, turn count, context usage, and usage totals from the last export. Label these as observations at a timestamp, rather than live service health.

Display the experiment settings, schedule, learning mode, risk limits, participant display names, and bounded discussion settings as read-only values. Operate pause/resume, retries, synthetic runs, model/risk changes, learning approvals, rollback, and meeting enablement through the Linux CLI. Pause/resume gates new research and meetings; existing positions retain their exit and recovery workflows. Record every operator change in the audit log and include relevant outcomes in a later publication.

The website remains usable from its last deployment when Linux is offline. Use snapshot age and the published next-update expectation to display a neutral "No newer snapshot has been published" notice; an old snapshot alone does not establish that a specific backend job failed.

## 13. Website publishing, GitHub, and static delivery

### Publishing responsibility

Implement a **Website Publisher** component whose job is to deliver existing, verified experiment records to the website. It runs on Linux after Monday research/purchases, Friday results/review, and Sunday meetings, plus explicitly requested operator publishes. It updates generated data and article content; frontend components and application logic remain developer-maintained source files.

The core exporter and Git operations are deterministic Python code. This component can be called the Publishing Agent in the product, but serializing records and delivering them does not require a language model. Copy financial values, attribution, accepted meeting speech, and validated reviews from their source records exactly. Preserve source IDs and versions so every published value is traceable.

An optional Codex editorial pass may produce a short site introduction or teaser from the approved snapshot. Keep this optional and disabled by default: the manager already supplies meeting titles/recaps and the analyst already supplies a weekly review. When enabled, run it in a fresh bounded context, request structured text with evidence references, and restrict its output to editorial fields. Keep accounting, transcript assembly, path selection, validation, credentials, commits, and publishing in application code. An editorial failure falls back to deterministic summaries. Give this optional role its own `CODEX_MODEL_PUBLISHER` setting and purpose `PUBLISHER_EDITORIAL`, an input budget of at most 6,000 estimated tokens, and a strict output schema limited to a 120-character heading, 500-character teaser, and valid evidence IDs. Supply only the current approved export and fixed editorial instructions, with publication credentials held by application code.

### Export contract

Create versioned Pydantic/JSON Schemas for the website data, with matching frontend validators/types. Export a coherent snapshot from a consistent database read, using only committed records. Include:

- Snapshot ID, source revision, export schema version, creation time, source cutoff, valuation time, and the next expected publication window.
- Account overview, complete published equity/return series, positions, fills, and performance summaries.
- Weekly indexes/details containing both researcher proposals, manager decisions, outcomes, analyst reviews, and evidence references.
- Learning state, bounded lessons, overlay versions/diffs, and validation/rollback history approved for display.
- Meeting indexes/details, participant identities, exact accepted turns, editorial metadata, and safe provenance.
- Read-only settings and sanitized operations/incident summaries.
- Sanitized downloadable transcripts and CSV/JSON views.

Represent monetary amounts as decimal strings or integer minor units with an explicit currency. Document probability/return units. Derive displayed profit from deterministic accounting, not narrative text. Use stable record IDs, stable slugs, explicit corrections, and explicit missing-data states.

Make `manifest.json` identify the complete export revision and list relative file paths, schema versions, and content hashes; exclude the manifest's own hash from its file list. Generate a revision's metadata once and reuse it on retries. Re-publishing an unchanged source/configuration revision is a no-op rather than a fresh timestamp-only commit. Keep compact per-week/per-meeting files so the site loads only the data needed for the selected view.

Retain detailed raw market feeds, authentication/configuration secrets, complete database backups, and diagnostic process output in protected Linux storage. Export an allowlisted presentation subset. Include licensed evidence excerpts only where redistribution is permitted; represent withheld evidence by safe metadata and source references. Sanitize Markdown as content, with raw HTML and executable extensions disabled. Render the JSON transcript and Markdown download from the same accepted turn records.

### Publication transaction

Implement an idempotent publication job:

1. Freeze a consistent export revision in the database and create a publication record.
2. Generate files into a temporary directory. Validate schemas, IDs, links, figures, file sizes, allowed paths, content safety, and completeness.
3. In a dedicated publisher checkout, fetch the configured remote branch and start from its current head. Apply the generated files only to allowlisted generated paths under `frontend/public/data/`, `frontend/public/transcripts/`, and `frontend/content/meetings/`.
4. Inspect the staged diff and run content validation plus the locked frontend static build. Commit the whole snapshot atomically, including its indexes and article files. Record the snapshot ID in the commit message.
5. Push normally to the configured publication/production branch. On a concurrent-update rejection, refresh the remote state and reapply/revalidate the generated snapshot with bounded retries. Preserve developer changes and refuse ambiguous conflicts. An already-delivered or superseded snapshot is recognized instead of duplicated or published over a newer revision.
6. Let Vercel's Git integration build the commit and publish the static output. Keep Git acceptance and deployment success as separate states.
7. Record the source revision, snapshot ID, Git commit, changed paths, validation results, attempts, and delivery status locally. When deployment verification is configured, perform bounded checks for the expected snapshot manifest on the deployed site or for a matching successful deployment. Private-site checks use an operator-configured protected automation mechanism. Without verification, report `PUSHED_UNVERIFIED`, not a claimed successful deployment.

Normally commit once after each complete workflow, including a labeled partial/failed result when appropriate. Retry publication without rerunning research, financial effects, reviews, or meeting speech. A GitHub or Vercel failure leaves the last successful website available and an incident visible locally. Later publication can recover directly to the newest consistent snapshot.

Use states such as `EXPORTING`, `VALIDATED`, `COMMITTED`, `PUSHED_UNVERIFIED`, `DEPLOYED`, `FAILED`, and `SUPERSEDED`. Serialize publishers per repository/branch. The next exported Operations view may include the last previously verified delivery; avoid recursive commits merely to announce the delivery of the current commit.

### GitHub and Vercel configuration

Use a private GitHub monorepo by default, import it into Vercel, select `frontend/` as the project root, and configure a production branch such as `main`. Verify that generated-data-only changes trigger builds. Validate all content again as part of the Vercel build. Lock dependencies and pre-render meeting and week routes using their exported indexes and `generateStaticParams` [R2]. Serve charts and client-side filters using the generated assets from that same deployment.

Use a dedicated GitHub publishing identity with minimum repository permissions. A fine-grained token limited to this repository and contents read/write is a practical single-owner setup; a scoped GitHub App is suitable for a longer-lived integration [R4]. Keep credentials in protected Linux configuration and out of prompts, file content, remote URLs, logs, frontend bundles, and commits. Enforce allowed changed paths in publishing code; repository-scoped credentials are not themselves a per-folder security boundary.

Document token rotation, repository rules, and the chosen automated commit author's compatibility with Vercel deployment permissions. Test a real generated-content commit end to end using synthetic data before enabling experiment publication. Preserve repository protections rather than disabling them silently; use an approved automation identity and an explicitly documented allowed branch/merge path.

Vercel receives source files and the sanitized export through its Git integration. The static build uses those committed inputs and declared dependencies. Keep backend/database/provider/Codex credentials on Linux. Browser navigation and data reads address the deployed Vercel assets, not authenticated raw GitHub content or the Linux engine.

### Access policy

Default `SITE_VISIBILITY=private`. Preserve private viewing with hosting-level access control that covers production domains, preview/deployment URLs, article pages, JSON, and transcript downloads. Verify access anonymously on a synthetic deployment before publishing the real research archive. Treat privacy configuration as part of deployment acceptance.

A private GitHub repository controls repository access, not the separate website audience. Vercel distinguishes protection scopes: Standard Protection excludes production domains, while All Deployments covers them; available methods/scopes depend on the current plan [R3]. Check the actual plan and settings. When the required private-production protection is unavailable, keep real-data publication disabled and report the requirement; the owner may explicitly configure `SITE_VISIBILITY=public` to publish the approved sanitized content instead.

Use client-side UI for presentation and interaction, and hosting access control for authorization. Treat exported/downloadable data and content shipped in browser bundles as accessible to everyone authorized to view that deployment. Protect historical deployments as well as the current domain. Document that Git stores past committed content, making pre-publication redaction essential.

## 14. Persistence and worker reliability

Create normalized tables with migrations for these domains:

| Domain | Records |
|---|---|
| Experiment and accounting | Experiments, accounts, cash ledger, positions, orders, fills, equity/benchmark snapshots, risk events |
| Weekly research | Weekly cycles, universe/data snapshots, proposals, evidence, manager decisions/allocations, reviews |
| Agent execution | Agents, runs, attempts, Codex metadata, usage, validated outputs |
| Prompts and context | Base-prompt versions, compiled inputs, hashes, context manifests |
| Learning | Memory items, patches, overlays/versions, evaluations, rollbacks |
| Team meetings | Meetings, frozen context snapshots, ordered turns, turn attempts/run links, publication versions, bounded recaps/follow-ups |
| Publication | Export revisions, manifests, file hashes, publish attempts, Git commits, delivery verification |
| Operations | Jobs, attempts, weekly invocations, operator audit events, incidents |

Use UTC timestamps, foreign keys, explicit statuses, uniqueness constraints, and suitable indexes. Preserve historical decisions and accounting; apply corrections through new versioned or reversal records.

Implement a PostgreSQL queue with transactional job claiming, for example `FOR UPDATE SKIP LOCKED`. Include idempotency key, payload, priority, status, attempts, next attempt, deadline, timeout, heartbeat, and terminal error.

Use leases or equivalent safeguards to recover abandoned jobs and prevent stale workers from committing duplicate results. Serialize account-changing stages per experiment and weekly cycle while allowing the two independent researcher subprocesses to run concurrently.

Treat cron delivery, worker attempts, agent execution, and committed financial effects as separately observable events. Commit each financial effect and its idempotency marker transactionally.

Give the Sunday root job its own meeting state and turn cursor. Commit an accepted turn and its state transition atomically; identify a meeting uniquely by experiment and scheduled Sunday date, and identify a turn by meeting and sequence number. Link every turn to the actual role-specific Codex run. Store source-week and upcoming-week references separately from the meeting date. Version article metadata and preserve accepted dialogue when retrying export or deployment. Link published content to its export revision and Git commit. Monday readiness depends on account and trading state, independently of meeting or publication success.

## 15. Native Linux, GitHub, and Vercel setup

Deliver a working deployment path using:

- Dedicated service account, such as `aiinvest`.
- Engine code under `/opt/ai-investment-lab` and a Python virtual environment at `.venv`.
- Mutable state, locks, isolated Codex workspaces, and an independent publishing checkout under `/var/lib/ai-investment-lab`.
- Protected configuration with explicit process-level read permissions and a separate publishing credential.
- A worker systemd unit with working directory, environment, restart behavior, logging, and resource limits.
- Three timezone-verified cron wrappers and entries for Monday, Friday, and Sunday.
- PostgreSQL provisioning, migrations, least-privilege roles, backups, and restore instructions.
- Codex installation, service-account login, preflight, and authentication recovery instructions.
- Git, the supported Node.js/package-manager toolchain for static-build validation, and documented GitHub credential/identity setup.
- GitHub repository and Vercel import instructions, project root, production branch, locked build commands, output directory, deployment access policy, and a synthetic content-push verification.

Run the application as an unprivileged service account. Separate the Codex execution environment from Git publishing permissions. Restrict local process and filesystem access so model/tool sessions receive only their approved workspace and authentication needs, while database/provider/publishing secrets stay with the relevant application services.

Provide an operator CLI for preflight, current status, full synthetic cycles, pause/resume, stage retries, learning approval/rollback, settings changes, and publication. Include commands equivalent to:

```bash
python -m app.cli status
python -m app.cli run-open-cycle
python -m app.cli run-close-cycle
python -m app.cli run-sunday-meeting
python -m app.cli publish-site --dry-run
python -m app.cli publish-site
```

Keep the cron entrypoints as thin wrappers around shared application services. Implement safe defaults, confirmation for consequential manual actions, deadlines, idempotency, and audit records.

Document systemd and journald operations, database recovery, failed/missed-week recovery, publisher authentication renewal, failed static builds, and restoring the site from committed content. A Git rollback affects displayed content only; it does not reverse trades, ledger history, or approved lessons in PostgreSQL. Protect backups and rotate credentials independently of the website deployment.

## 16. Testing

Implement automated tests with synthetic market data and a fake Codex executable so the complete development workflow is deterministic.

Cover:

1. **Accounting:** Exact initial capital, cash/quantity conservation, costs, precision, reconciliation, allocation limits, corporate actions, partial fills, and unsupported exit prices.
2. **Scheduling:** Three weekly triggers, timezone behavior, calendar skips, deadlines, repeated invocations, manual retry, missed triggers, restart recovery, and Sunday meetings after skipped trading weeks.
3. **Workflow:** Independent research, manager prerequisites, hold-cash outcomes, risk validation, Friday liquidation before analysis, and completed-stage preservation.
4. **Codex:** Argument-array construction, fresh isolated runs, structured output, model settings, timeouts, process-group termination, bounded retries, authentication failures, and malformed/oversized responses.
5. **Context:** Section/total limits, eight-summary window, older aggregates, 12-lesson cap, 700-character limit, deterministic manifests, and fresh input across successive weeks.
6. **Learning:** Allowed patches, evidence validation, three-patch activation cap, approval modes, expiry, rollback, and next-cycle inclusion of the exact overlay version.
7. **Data integrity:** Cutoff enforcement, stale/delayed data, valid evidence references, matched comparison windows, and separation of synthetic and real-data experiments.
8. **Security and UI:** Sanitized exports, protected deployment access including JSON/downloads, secret exclusion, read-only presentation, local operator authorization, dashboard/accounting agreement, and all required process views.
9. **Deployment:** Static export build, generated week/meeting routes, worker startup, migrations, systemd unit, three cron wrappers, content-only Git push, and an end-to-end synthetic week through static Sunday publication.
10. **Meetings:** Manager opens and closes; each participant generates its own updates and replies; validated turn routing and references; natural dialogue rendered in order; bounded prompts/transcript/recap; role and model provenance; duplicate-run protection; failed-turn recovery; degraded participation; export retries; statically generated article/archive/download; account and overlay state remain unchanged by discussion.
11. **Publishing:** Consistent source revision, exact ledger values, schema validation, allowed changed paths, secret/content filtering, canonical transcript equality, one coherent commit, unchanged-export no-op, concurrent pushes, duplicate job recovery, superseded snapshots, deployment failure/unknown status, and independent publication retries.
12. **Static behavior:** Website works when Linux is unavailable; network requests use deployed assets; data freshness is explicit; planned work is distinct from observed completion; chart/filter interactions work; all linked static routes and downloads exist. Use fake Git/deployment transports for CI, and separately document the real GitHub/Vercel smoke test.

Add a multi-week synthetic integration test that proves the analyst's accepted patch changes the next applicable agent prompt while context remains bounded and ledger results remain reproducible. Include Friday review, Sunday discussion, export/Git/static build, and next-Monday research in one test: conversation uses actual prior outcomes, article speech matches accepted turns, researchers receive their own approved overlays, and archived meetings do not accumulate in their input. Test both a first-ever kickoff meeting and a skipped or failed trading week.

## 17. Implementation and deliverables

Build in runnable stages:

1. Repository, configuration, migrations, synthetic provider, and paper ledger.
2. Weekly state machines, durable worker, operator CLI, three cron entrypoints, and risk/execution engine.
3. Fake and real Codex runners, schemas, prompt compiler, and role prompts.
4. Research, manager, Friday review, and bounded learning workflows.
5. Sunday meeting orchestrator, conversational prompts, accepted turns, and article generation.
6. Website export contracts, deterministic publisher, Git delivery, and fake transports.
7. Next.js static dashboard with proposals, results, reviews, lessons, meeting articles, and local interactions.
8. Real market-data adapter, native Linux deployment, GitHub/Vercel configuration, access verification, and end-to-end testing.

Deliver working source code, dependency lockfiles, documented `.env.example` placeholders, migrations, fixtures, role/export schemas, prompt files, fake Codex/Git/deployment test doubles, worker service file, cron wrappers/configuration, generated synthetic site content, Vercel build configuration, and automated tests.

Include:

- `README.md` with an end-to-end synthetic quickstart and static-site preview.
- `docs/architecture.md` and `docs/agent-contracts.md`.
- `docs/native-linux-deployment.md` and `docs/github-vercel-deployment.md`.
- `docs/codex-runner.md` and `docs/context-and-memory.md`.
- `docs/learning-methodology.md` and `docs/paper-trading.md`.
- `docs/team-meetings.md` with agenda, per-turn runs, bounds, dialogue generation, and recovery.
- `docs/website-publisher.md` with source-of-truth boundaries, export schemas, paths, Git identity, credential rotation, retries, delivery verification, freshness, and access policy.
- `docs/operations.md` with CLI examples, cron changes, backups, recovery, and manual learning controls.
- A UI walkthrough or screenshots from an actual synthetic static build.
- Explicit assumptions, data/redistribution limitations, executed verification, and outstanding work.

## 18. Acceptance criteria

A developer can clone the repository onto Linux, create the virtual environment, configure PostgreSQL, run migrations, authenticate Codex, install the worker and three cron entries, configure a restricted GitHub publishing identity, and connect Vercel to `frontend/` in the repository.

A complete synthetic run visibly demonstrates:

1. The $1,000 starting account.
2. Both investing agents' proposals and evidence.
3. The manager's selections, allocations, and rationale.
4. Simulated Monday purchases and Friday sales with reconciled results.
5. The analyst's review and learning patches.
6. The accepted overlay in the next applicable bounded agent prompt.
7. A complete research timeline and reproducible local audit records.
8. Correct behavior when a workflow is retried or interrupted.
9. A Sunday meeting in which the manager leads and every available role produces its own context-aware speech.
10. A complete blog-style static article and archive with accurate attribution and links to the corresponding week.
11. Bounded discussion context with account state and formal learning versions preserved.
12. Automatic publication of verified data/content files to GitHub, followed by a Vercel static deployment showing the corresponding revision.
13. Frontend component source remains unchanged during data-only publication.
14. The website remains readable when Linux is unavailable and clearly states the snapshot/valuation dates.
15. Publication retry preserves financial history and accepted meeting messages.
16. The configured private access policy protects all deployed pages/assets, or an explicit owner-approved public mode is documented.
17. Operator actions work through the Linux CLI and their results appear in the next website snapshot.

The same application then runs forward paper experiments with the configured market data provider and fresh Codex CLI processes. A Git push, a completed static build, and a verified live deployment are reported as distinct verification steps.

## 19. Platform implementation references

The platform capabilities below were checked on 2026-10-11. Verify the installed versions, current hosting plan, repository permissions, and deployment settings during implementation. Use these references for the selected design, not as additional feature requirements.

- **[R1] Vercel GitHub integration:** Git-triggered deployments, production/preview behavior, and automation author permissions.
- **[R2] Next.js static exports:** `output: 'export'`, build-time data loading, static asset output, and generated dynamic paths.
- **[R3] Vercel deployment protection:** Protection methods, production-domain scope, and plan-specific availability.
- **[R4] GitHub authentication:** Fine-grained repository permissions and credentials for automation.

```text
[R1] https://vercel.com/docs/git/vercel-for-github
     https://vercel.com/docs/git
[R2] https://nextjs.org/docs/app/guides/static-exports
[R3] https://vercel.com/docs/deployment-protection
[R4] https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens
```

Make reasonable implementation decisions for minor unspecified details and record material assumptions. Report completion based on implemented features and executed tests, with any remaining limitations stated explicitly.
