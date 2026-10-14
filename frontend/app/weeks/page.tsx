import { weeks } from "@/lib/data";
import { Heading, Panel } from "@/components/ui";
import History from "@/components/history";
export default function Weeks() {
  return (
    <>
      <Heading title="Weeks" description="Decisions, trades and results." />
      <Panel title="Weekly activity">
        <History weeks={weeks()} />
      </Panel>
    </>
  );
}
