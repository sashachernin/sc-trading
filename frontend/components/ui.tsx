import Link from "next/link";
import { ArrowUpRight, Clock3 } from "lucide-react";
export function Badge({ status }: { status: string }) {
  return (
    <span
      className={`badge ${status.includes("COMPLETED") || status.includes("READY") || status === "ACTIVE" ? "good" : status.includes("FAIL") || status.includes("RECOVERY") ? "bad" : "neutral"}`}
    >
      {status.replaceAll("_", " ").toLowerCase()}
    </span>
  );
}
export function Heading({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </div>
  );
}
export function Panel({
  title,
  children,
  aside,
  className = "",
}: {
  title: string;
  children: React.ReactNode;
  aside?: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`panel ${className}`}>
      <div className="panel-heading">
        <h2>{title}</h2>
        {aside}
      </div>
      {children}
    </section>
  );
}
export function Empty({ text }: { text: string }) {
  return <div className="empty">{text}</div>;
}
export function ArticleCard({
  id,
  title,
  date,
  excerpt,
  minutes,
  status,
}: {
  id: string;
  title: string;
  date: string;
  excerpt: string;
  minutes: number;
  status: string;
}) {
  return (
    <Link href={`/meetings/${id}/`} className="article-card">
      <div className="article-meta">
        <span>THE SUNDAY DISCUSSION</span>
        <span>{date}</span>
      </div>
      <h3>{title}</h3>
      <p>{excerpt}</p>
      <div className="article-bottom">
        <span>
          <Clock3 size={14} />
          {minutes} min read · {status.replaceAll("_", " ").toLowerCase()}
        </span>
        <ArrowUpRight size={18} />
      </div>
    </Link>
  );
}
