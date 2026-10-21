import Image from "next/image";
import { names } from "@/lib/data";

export default function AgentAvatar({ agent }: { agent: string }) {
  const person = names[agent];
  return (
    <span className={`avatar ${person.color}`}>
      <Image src={person.avatar} alt="" width={64} height={64} />
    </span>
  );
}
