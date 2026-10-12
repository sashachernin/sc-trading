import Execution from "@/components/execution";
import Link from "next/link";
import { week, weeks, names, usd, percent } from "@/lib/data";
import { Heading, Panel, Badge, Empty } from "@/components/ui";
export function generateStaticParams() {
  return weeks().map((w) => ({ weekId: w.id }));
}
export default async function WeekPage({
  params,
}: {
  params: Promise<{ weekId: string }>;
}) {
  const { weekId } = await params;
  const w = week(weekId);
  const selected = new Set(w.decision?.allocations.map((a) => a.proposal_id));
  return (
    <>
      <Link href="/weeks/" className="back">
        ← Weekly research
      </Link>
      <Heading
        eyebrow="PAPER / SIMULATED · WEEKLY RECORD"
        title={`Week of ${w.monday}`}
        description={
          w.data.reason ||
          "The complete proposal-to-review record for this cycle."
        }
        action={<Badge status={w.status} />}
      />
      <div className="metrics compact">
        <div className="metric">
          <span>Starting equity</span>
          <strong>
            {w.data.starting_equity
              ? usd(w.data.starting_equity)
              : "Unavailable"}
          </strong>
        </div>
        <div className="metric">
          <span>Net paper P&L</span>
          <strong>{w.data.pnl ? usd(w.data.pnl) : "Unavailable"}</strong>
        </div>
        <div className="metric">
          <span>Ending equity</span>
          <strong>
            {w.data.ending_equity ? usd(w.data.ending_equity) : "Unavailable"}
          </strong>
        </div>
        <div className="metric">
          <span>Benchmark return</span>
          <strong>
            {w.data.benchmark_return
              ? percent(w.data.benchmark_return)
              : "Unavailable"}
          </strong>
        </div>
      </div>
      <div className="research-grid">
        {["researcher_a", "researcher_b"].map((role) => (
          <Panel title={`${names[role].name} · ${names[role].role}`} key={role}>
            {w.proposals
              .filter((p) => p.role === role)
              .map((p) => (
                <div key={p.id} className="proposal">
                  <div className="proposal-heading">
                    <strong>
                      <span className="rank">{p.rank}</span>
                      {p.ticker}
                    </strong>
                    <Badge
                      status={selected.has(p.id) ? "SELECTED" : "REJECTED"}
                    />
                  </div>
                  <p>{p.thesis}</p>
                  <div className="proposal-stats">
                    <span>
                      Expected <strong>{percent(p.expected_return)}</strong>
                    </span>
                    <span>
                      Downside <strong>{percent(p.downside)}</strong>
                    </span>
                    <span>
                      Confidence <strong>{percent(p.confidence)}</strong>
                    </span>
                    <span>
                      Profit probability{" "}
                      <strong>{percent(p.probability_profit)}</strong>
                    </span>
                  </div>
                  <details>
                    <summary>Evidence, catalysts & assumptions</summary>
                    <p>
                      <strong>Catalysts:</strong> {p.catalysts.join("; ")}
                    </p>
                    <p>
                      <strong>Risks:</strong> {p.risks.join("; ")}
                    </p>
                    <p>
                      <strong>Invalidation:</strong> {p.invalidation}
                    </p>
                    <p>
                      <strong>Assumptions:</strong> {p.assumptions.join("; ")}
                    </p>
                    <p>
                      <strong>Evidence IDs:</strong> {p.evidence_ids.join(", ")}
                    </p>
                  </details>
                </div>
              ))}
            {!w.proposals.some((p) => p.role === role) && (
              <Empty text="No accepted proposals. See run status or skip reason." />
            )}
          </Panel>
        ))}
      </div>
      <Panel title="Casey’s capital decision">
        {w.decision ? (
          <>
            <p className="narrative">{w.decision.summary}</p>
            <div className="decision-grid">
              {w.decision.allocations.map((a) => (
                <div className="allocation" key={a.proposal_id}>
                  <span>
                    {w.proposals.find((p) => p.id === a.proposal_id)?.ticker}
                  </span>
                  <strong>
                    {usd(a.amount)} <small>· {percent(a.percent)}</small>
                  </strong>
                  <p>{a.rationale}</p>
                </div>
              ))}
              <div className="allocation">
                <span>Retained cash budget</span>
                <strong>{usd(w.decision.retained_cash)}</strong>
                <p>
                  Actual cash includes deterministic fill rounding and fees.
                </p>
              </div>
            </div>
            <p className="subtle">Uncertainty: {w.decision.uncertainty}</p>
            <details>
              <summary>Rejected proposals & deterministic risk checks</summary>
              {w.decision.rejections.map((r) => (
                <p key={r.proposal_id}>
                  <strong>
                    {w.proposals.find((p) => p.id === r.proposal_id)?.ticker}:
                  </strong>{" "}
                  {r.rationale}
                </p>
              ))}
              <p>{w.data.risk_checks?.join(" · ")}</p>
            </details>
          </>
        ) : (
          <Empty text="No accepted manager decision for this cycle." />
        )}
      </Panel>
      <Execution fills={w.fills || []} />
      <Panel title="Riley’s Friday review">
        {w.review ? (
          <>
            <p className="narrative">{w.review.summary}</p>
            <div className="scorecards">
              {w.review.scorecards.map((s) => (
                <div key={s.role}>
                  <span>{names[s.role].name}</span>
                  <strong>{percent(s.score)}</strong>
                  <p>{s.assessment}</p>
                </div>
              ))}
            </div>
            <p>{w.review.selected_vs_rejected}</p>
            <p>{w.review.execution_effects}</p>
            <div className="mini-note">{w.review.limitations}</div>
            <details>
              <summary>Forecast comparisons, successes & weaknesses</summary>
              {w.review.forecast_comparisons.map((x, i) => (
                <p key={i}>{x}</p>
              ))}
              <p>Successes: {w.review.successes.join("; ")}</p>
              <p>Weaknesses: {w.review.weaknesses.join("; ")}</p>
            </details>
          </>
        ) : (
          <Empty text="Review unavailable; no analyst conclusion is inferred." />
        )}
      </Panel>
      <div className="research-grid">
        <Panel title="Committed timeline">
          <ol className="timeline">
            {w.timeline.map((t) => (
              <li key={t.stage}>
                <strong>{t.stage.replaceAll("_", " ").toLowerCase()}</strong>
                <time>{new Date(t.completed_at).toUTCString()}</time>
              </li>
            ))}
          </ol>
        </Panel>
        <Panel title="Run provenance & bounded context">
          {w.runs.map((r) => (
            <details key={r.id}>
              <summary>
                {names[r.role]?.name} · {r.purpose.toLowerCase()} ·{" "}
                {r.status.toLowerCase()}
              </summary>
              <p>Model: {r.model || "Unavailable"}</p>
              <pre>{JSON.stringify(r.manifest, null, 2)}</pre>
              <p className="subtle">Sanitized fixed-instruction excerpt</p>
              <pre>{r.prompt_excerpt}</pre>
            </details>
          ))}
        </Panel>
      </div>
      {w.meeting_ids.map((id) => (
        <Link key={id} href={`/meetings/${id}/`} className="button">
          Read the linked Sunday discussion →
        </Link>
      ))}
      <a className="text-link" href={`/data/weeks/${w.id}.json`}>
        Download this paper research record
      </a>
    </>
  );
}
