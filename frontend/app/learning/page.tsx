import Link from "next/link";
import { lessons, names } from "@/lib/data";
import { Heading, Panel, Badge } from "@/components/ui";
export default function Learning() {
  const ls = lessons();
  return (
    <>
      <Heading
        title="Learning"
        description="What the team is taking into the next week."
      />
      {!ls.length ? (
        <Panel title="Lessons">
          <p className="empty">
            The first lessons will appear after Friday’s review.
          </p>
        </Panel>
      ) : (
        ["researcher_a", "researcher_b", "manager"]
          .filter((role) => ls.some((l) => l.role === role))
          .map((role) => (
            <Panel key={role} title={names[role].name}>
              {ls
                .filter((l) => l.role === role)
                .map((l) => (
                  <div className="lesson" key={l.id}>
                    <Badge status={l.status} />
                    <h3>{l.text}</h3>
                    <p>{l.expected_effect}</p>
                    <Link href={`/weeks/${l.week_id}/`}>View the week →</Link>
                  </div>
                ))}
            </Panel>
          ))
      )}
    </>
  );
}
