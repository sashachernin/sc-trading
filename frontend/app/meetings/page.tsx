import { meetings } from "@/lib/data";
import { Heading } from "@/components/ui";
import Archive from "@/components/archive";
export default function Meetings() {
  return (
    <>
      <Heading title="Meetings" description="The team’s Sunday discussion." />
      <Archive items={meetings()} />
    </>
  );
}
