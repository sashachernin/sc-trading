import Execution from "@/components/execution";
import Link from "next/link";
import { week, weeks, names, usd } from "@/lib/data";
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
  const bought = [
    ...new Set(
      (w.fills || []).filter((f) => f.side === "BUY").map((f) => f.ticker),
    ),
  ];
  const date = new Date(`${w.monday}T12:00:00Z`).toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
  return (
    <>
      <Link href="/weeks/" className="back">
        ← All weeks
      </Link>
      <Heading title={`Week of ${date}`} action={<Badge status={w.status} />} />
      <Panel title="This week">
        <p className="narrative">
          {bought.length
            ? `Bought ${bought.join(", ")}. ${w.status === "COMPLETED" ? "The week is complete." : "Friday’s results are still pending."}`
            : w.decision
              ? "The firm chose to hold cash."
              : w.data.reason || "The team is preparing its decision."}
        </p>
        <div className="metrics compact">
          <div className="metric">
            <span>Starting balance</span>
            <strong>
              {w.data.starting_equity ? usd(w.data.starting_equity) : "—"}
            </strong>
          </div>
          <div className="metric">
            <span>Allocated</span>
            <strong>
              {w.decision
                ? usd(
                    String(
                      w.decision.allocations.reduce(
                        (total, a) => total + Number(a.amount),
                        0,
                      ),
                    ),
                  )
                : "—"}
            </strong>
          </div>
          <div className="metric">
            <span>
              {w.data.pnl !== undefined
                ? "Weekly result"
                : "Current gain / loss"}
            </span>
            <strong>
              {w.data.pnl !== undefined
                ? usd(w.data.pnl)
                : w.data.current_pnl !== undefined
                  ? usd(w.data.current_pnl)
                  : "Pending"}
            </strong>
          </div>
        </div>
      </Panel>
      <Panel title="Casey’s decision">
        {w.decision ? (
          <>
            <div className="decision-grid">
              {w.decision.allocations.map((a) => (
                <div className="allocation" key={a.proposal_id}>
                  <span>
                    {w.proposals.find((p) => p.id === a.proposal_id)?.ticker}
                  </span>
                  <strong>{usd(a.amount)}</strong>
                </div>
              ))}
              <div className="allocation">
                <span>Cash kept</span>
                <strong>{usd(w.decision.retained_cash)}</strong>
              </div>
            </div>
            <details>
              <summary>Why this decision?</summary>
              <p>{w.decision.summary}</p>
              {w.decision.allocations.map((a) => (
                <p key={a.proposal_id}>{a.rationale}</p>
              ))}
              {w.decision.rejections.map((r) => (
                <p key={r.proposal_id}>
                  <strong>
                    {w.proposals.find((p) => p.id === r.proposal_id)?.ticker}:
                  </strong>{" "}
                  {r.rationale}
                </p>
              ))}
            </details>
          </>
        ) : (
          <Empty text="No decision yet." />
        )}
      </Panel>
      <Execution fills={w.fills || []} />
      <Panel title="Ideas the team considered">
        {w.proposals.length ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Stock</th>
                  <th>Suggested by</th>
                  <th>Decision</th>
                  <th>Research</th>
                </tr>
              </thead>
              <tbody>
                {w.proposals.map((p) => (
                  <tr key={p.id}>
                    <td>
                      <strong>{p.ticker}</strong>
                      <br />
                      <small>{p.company}</small>
                    </td>
                    <td>{names[p.role]?.name}</td>
                    <td>
                      {w.decision ? (
                        <Badge
                          status={selected.has(p.id) ? "SELECTED" : "REJECTED"}
                        />
                      ) : (
                        "Pending"
                      )}
                    </td>
                    <td>
                      <details>
                        <summary>Read idea</summary>
                        <p>{p.thesis}</p>
                        <p>
                          <strong>Risks:</strong> {p.risks.join("; ")}
                        </p>
                      </details>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty text="No stock ideas this week." />
        )}
        {["researcher_a", "researcher_b"].map((role) => {
          const report = w.runs
            .filter((r) => r.purpose === "RESEARCH" && r.role === role)
            .at(-1);
          return (
            report && (
              <details key={role}>
                <summary>{names[role].name}’s research notes</summary>
                <p>
                  {report.research_summary ||
                    report.abstention_reason ||
                    "No notes available."}
                </p>
                {!!report.sources?.length && (
                  <details>
                    <summary>Sources</summary>
                    <ul>
                      {report.sources.map((s) => (
                        <li key={s.id}>
                          <a
                            href={s.url}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            {s.title} ↗
                          </a>
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
              </details>
            )
          );
        })}
      </Panel>
      <Panel title="Friday review">
        {w.review ? (
          <>
            <p>{w.review.summary}</p>
            <details>
              <summary>What Riley learned</summary>
              <p>{w.review.selected_vs_rejected}</p>
              <p>{w.review.successes.join("; ")}</p>
              <p>{w.review.weaknesses.join("; ")}</p>
            </details>
          </>
        ) : (
          <Empty text="Available after Friday’s close." />
        )}
      </Panel>
      {w.meeting_ids.map((id) => (
        <Link key={id} href={`/meetings/${id}/`} className="button">
          Read the team discussion →
        </Link>
      ))}
    </>
  );
}
