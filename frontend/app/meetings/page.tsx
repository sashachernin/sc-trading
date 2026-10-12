import { meetings } from "@/lib/data";
import { Heading } from "@/components/ui";
import Archive from "@/components/archive";
export default function Meetings() {
  return (
    <>
      <Heading
        eyebrow="THE SUNDAY TABLE"
        title="Good questions make better research."
        description="Four AI colleagues compare notes, challenge assumptions, and talk through the week. Actual accepted dialogue, in order."
      />
      <div className="meeting-banner">
        <span className="eyebrow">AI-GENERATED TEAM DISCUSSION</span>
        <p>
          Paper-trading research, with uncertainty left in the conversation.
          Meetings observe the experiment; formal lessons pass through Friday’s
          learning gate.
        </p>
      </div>
      <Archive items={meetings()} />
    </>
  );
}
