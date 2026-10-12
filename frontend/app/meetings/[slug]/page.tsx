import Link from "next/link";
import { notFound } from "next/navigation";
import { meeting, meetings, names, usd } from "@/lib/data";
import { Badge } from "@/components/ui";
export function generateStaticParams() {
  const records = meetings();
  return records.length
    ? records.map((m) => ({ slug: m.id }))
    : [{ slug: "no-published-meetings" }];
}
export default async function Article({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  if (!meetings().some((m) => m.id === slug)) notFound();
  const m = meeting(slug),
    archive = meetings(),
    i = archive.findIndex((x) => x.id === slug);
  return (
    <article className="meeting-article">
      <Link href="/meetings/" className="back">
        ← Team meetings
      </Link>
      <div className="eyebrow">THE SUNDAY TABLE · {m.sunday}</div>
      <h1>{m.data.title}</h1>
      <p className="standfirst">{m.data.standfirst}</p>
      <div className="article-labels">
        <Badge status={m.status} />
        <span className="badge paper">AI-GENERATED · PAPER / SIMULATED</span>
        {m.data.synthetic && (
          <span className="badge">Synthetic test-double speech</span>
        )}
      </div>
      <div className="participants">
        {Object.entries(names).map(([role, p]) => (
          <div key={role}>
            <span className="avatar">{p.initials}</span>
            <span>
              {p.name}
              <small>{p.role}</small>
            </span>
          </div>
        ))}
      </div>
      <div className="week-recap">
        <span className="eyebrow">THE REFERENCED WEEK</span>
        <p>
          Status: {m.context.source.status.replaceAll("_", " ").toLowerCase()} ·
          Recorded net paper result:{" "}
          <strong>{usd(m.context.source.pnl)}</strong>
        </p>
        {m.week_id && (
          <Link href={`/weeks/${m.week_id}/`}>
            Open the week’s proposals and Friday review →
          </Link>
        )}
        <small>
          Source cutoff: {m.context.cutoff} · Actual generation:{" "}
          {m.data.generated_at}
        </small>
      </div>
      {m.status === "CONTENT_READY_PARTIAL" && (
        <p className="notice">
          Partial discussion. Unavailable participants:{" "}
          {m.data.unavailable.join(", ")}. Status notices are application
          records, not agent speech.
        </p>
      )}
      <div className="dialogue">
        {m.turns.map((t, index) => (
          <section key={t.id} className="turn">
            {(index === 0 || m.turns[index - 1].phase !== t.phase) && (
              <h2 className="phase">
                {t.phase === "opening"
                  ? "At the table"
                  : t.phase === "updates"
                    ? "The week, from each perspective"
                    : t.phase === "discussion"
                      ? "Questions worth carrying forward"
                      : "Before we go"}
              </h2>
            )}
            <div className="speaker">
              <span
                className={`avatar ${t.speaker === "manager" ? "sand" : t.speaker === "analyst" ? "rose" : t.speaker === "researcher_b" ? "blue" : "sage"}`}
              >
                {names[t.speaker].initials}
              </span>
              <div>
                <strong>{names[t.speaker].name}</strong>
                <span>{names[t.speaker].role}</span>
              </div>
              <span className="turn-number">
                {String(t.sequence).padStart(2, "0")}
              </span>
            </div>
            {t.message_markdown.split("\n\n").map((p, j) => (
              <p key={j}>{p}</p>
            ))}
          </section>
        ))}
      </div>
      <section className="article-recap">
        <h2>What we’re taking into next week</h2>
        <p>{m.data.recap}</p>
        <h3>Focus areas</h3>
        <ul>
          {m.data.focus_areas.map((x) => (
            <li key={x}>{x}</li>
          ))}
        </ul>
        <h3>Open questions</h3>
        <ul>
          {m.data.open_questions.map((x) => (
            <li key={x}>{x}</li>
          ))}
        </ul>
      </section>
      <details className="provenance">
        <summary>Source, run provenance & transcript</summary>
        <p>
          Upcoming cycle: {m.upcoming_monday}. Source packet frozen at{" "}
          {m.context.cutoff}.
        </p>
        {m.turns.map((t) => (
          <details key={t.id}>
            <summary>
              Turn {t.sequence} · {names[t.speaker].name}
            </summary>
            <pre>
              {JSON.stringify(
                {
                  id: t.id,
                  run_id: t.run_id,
                  evidence_ids: t.evidence_ids,
                  reply_to_turn_ids: t.reply_to_turn_ids,
                  ...t.provenance,
                },
                null,
                2,
              )}
            </pre>
          </details>
        ))}
        <a href={`/transcripts/${m.id}.md`} download>
          Download canonical Markdown transcript
        </a>
      </details>
      <div className="article-nav">
        {archive[i + 1] ? (
          <Link href={`/meetings/${archive[i + 1].id}/`}>
            ← Previous discussion
          </Link>
        ) : (
          <span />
        )}
        {archive[i - 1] && (
          <Link href={`/meetings/${archive[i - 1].id}/`}>
            Next discussion →
          </Link>
        )}
      </div>
    </article>
  );
}
