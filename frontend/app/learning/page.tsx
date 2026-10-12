import Link from "next/link";
import { lessons, names, percent } from "@/lib/data";
import { Heading, Panel, Badge, Empty } from "@/components/ui";
export default function Learning() {
  const ls = lessons();
  return (
    <>
      <Heading
        eyebrow="BOUNDED MEMORY"
        title="Learning, with a paper trail."
        description="Versioned hypotheses grounded in observed outcomes. Base prompts and financial rules remain application-controlled."
      />
      <div className="notice">
        At most 12 active lessons per role, 700 characters per lesson, and three
        new activations per week. Approval and rollback happen through the Linux
        CLI.
      </div>
      {["researcher_a", "researcher_b", "manager"].map((role) => (
        <Panel
          key={role}
          title={`${names[role].name} · ${ls.filter((l) => l.role === role && l.status === "ACTIVE").length} / 12 active lessons`}
        >
          {ls
            .filter((l) => l.role === role)
            .map((l) => (
              <div className="lesson" key={l.id}>
                <div>
                  <span className="eyebrow">
                    OVERLAY v{l.version} · {l.operation}
                  </span>
                  <Badge status={l.status} />
                </div>
                <h3>{l.text}</h3>
                <p>{l.expected_effect}</p>
                <div className="lesson-meta">
                  <span>Confidence {percent(l.confidence)}</span>
                  <span>Expires {l.expiry}</span>
                  <span>{l.mode.replaceAll("_", " ")}</span>
                  <Link href={`/weeks/${l.week_id}/`}>Supporting week →</Link>
                </div>
                <details>
                  <summary>Evidence, validation & rollback condition</summary>
                  <p>Evidence: {l.evidence_ids.join(", ")}</p>
                  <p>
                    Validation:{" "}
                    {l.validation_errors.length
                      ? l.validation_errors.join("; ")
                      : "Accepted within bounds"}
                  </p>
                  <p>Success metric: {l.success_metric}</p>
                  <p>Rollback: {l.rollback_condition}</p>
                  <p>
                    Diff: {l.status === "ROLLED_BACK" ? "−" : "+"} {l.text}
                  </p>
                </details>
              </div>
            ))}
          {!ls.some((l) => l.role === role) && (
            <Empty text="No lessons recorded for this role." />
          )}
        </Panel>
      ))}
    </>
  );
}
