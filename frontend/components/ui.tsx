export function Badge({ status }: { status: string }) {
  return (
    <span
      className={`badge ${status.includes("COMPLETED") || status.includes("READY") || status === "ACTIVE" ? "good" : status.includes("FAIL") || status.includes("RECOVERY") ? "bad" : "neutral"}`}
    >
      {(
        {
          OPEN: "Invested",
          HOLD_CASH: "Holding cash",
          COMPLETED: "Completed",
          RESEARCHING: "Researching",
          SELECTED: "Selected",
          REJECTED: "Passed",
          MISSED: "Missed",
          CONTENT_READY: "Published",
          CONTENT_READY_PARTIAL: "Partial",
          SKIPPED_NONSTANDARD_WEEK: "Skipped",
        } as Record<string, string>
      )[status] || status.replaceAll("_", " ").toLowerCase()}
    </span>
  );
}
export function Heading({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1>{title}</h1>
        {description && <p>{description}</p>}
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
