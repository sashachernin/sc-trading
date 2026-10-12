import { weeks } from "@/lib/data";
import { Heading, Panel } from "@/components/ui";
import History from "@/components/history";
export default function Weeks() {
  return (
    <>
      <Heading
        eyebrow="RESEARCH ARCHIVE"
        title="Every week, on the record."
        description="Independent proposals, capital decisions, paper fills, and the lessons that followed."
        action={
          <a className="button" href="/data/performance.csv" download>
            Download paper results CSV
          </a>
        }
      />
      <Panel title="Published weekly cycles">
        <History weeks={weeks()} />
      </Panel>
    </>
  );
}
