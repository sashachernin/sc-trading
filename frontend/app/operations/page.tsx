import { operations, manifest } from "@/lib/data";
import { Heading, Panel, Badge, Empty } from "@/components/ui";
export default function OperationsPage() {
  const o = operations(),
    m = manifest();
  return (
    <>
      <Heading
        eyebrow="LAST PUBLISHED OBSERVATIONS"
        title="The experiment behind the scenes."
        description="Operational records observed at export time. Linux logs and CLI status are authoritative for current service health."
        action={<Badge status={o.paused ? "PAUSED" : "ACTIVE"} />}
      />
      <div className="notice">
        Observed {o.observed_at}. Snapshot age does not establish that a job
        failed.
      </div>
      <div className="metrics">
        {Object.entries(o.queue).map(([status, count]) => (
          <div className="metric" key={status}>
            <span>{status.toLowerCase()} jobs</span>
            <strong>{count}</strong>
            <small>Queue observation at export</small>
          </div>
        ))}
      </div>
      <div className="research-grid">
        <Panel title="Experiment configuration">
          <dl className="settings">
            {[
              [
                "Mode",
                o.settings.synthetic
                  ? "Synthetic demonstration"
                  : "Forward paper research",
              ],
              ["Market data", o.settings.provider],
              ["Start / end", `${o.settings.start} / ${o.settings.end}`],
              ["Learning", o.settings.learning_mode],
              ["Site policy", o.settings.site_visibility],
              [
                "Private access check",
                o.settings.private_access_verified
                  ? "Operator verified"
                  : "Not yet verified",
              ],
              [
                "Ticker / deployment cap",
                `${Number(o.settings.max_stock_allocation) * 100}% / ${Number(o.settings.max_deployed) * 100}%`,
              ],
              [
                "Meeting / memory limits",
                `${o.settings.meeting_turn_limit} turns / ${o.settings.active_memory_cap} lessons`,
              ],
            ].map(([k, v]) => (
              <div key={k}>
                <dt>{k}</dt>
                <dd>{v}</dd>
              </div>
            ))}
          </dl>
        </Panel>
        <Panel title="Execution & delivery">
          <p>{o.worker_status}</p>
          <dl className="settings">
            {Object.entries(o.settings.models).map(([role, model]) => (
              <div key={role}>
                <dt>{o.settings.participants[role].name}</dt>
                <dd>{model}</dd>
              </div>
            ))}
          </dl>
          <div className="mini-note">
            Current source revision: {m.source_revision}
            <br />
            Previous delivery:{" "}
            {o.previous_delivery?.status || "No delivery verified"}
            <br />A validated export, Git push, and live deployment are distinct
            states.
          </div>
        </Panel>
      </div>
      <Panel title="Incident history">
        {o.incidents.length ? (
          o.incidents.map((i) => (
            <div className="incident" key={i.id}>
              <Badge status={i.category} />
              <p>{i.summary}</p>
              <small>{i.observed_at}</small>
            </div>
          ))
        ) : (
          <Empty text="No incidents recorded in this snapshot." />
        )}
      </Panel>
      <Panel title="Operator audit trail">
        {o.audit.length ? (
          o.audit.map((a, i) => (
            <div className="account-line" key={i}>
              <strong>{a.action}</strong>
              <span>{a.created_at}</span>
            </div>
          ))
        ) : (
          <Empty text="No manual operator changes recorded." />
        )}
      </Panel>
    </>
  );
}
