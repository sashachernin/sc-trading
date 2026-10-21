import AgentAvatar from "@/components/agent-avatar";
import Link from "next/link";
import { overview, weeks, meetings, usd } from "@/lib/data";
import { Heading, Panel, ArticleCard } from "@/components/ui";
import EquityChart from "@/components/chart";
import History from "@/components/history";
export default function Home() {
  const o = overview(),
    ws = weeks(),
    ms = meetings();
  return (
    <>
      <Heading
        title="Overview"
        action={
          <Link className="button" href="/weeks/">
            This week →
          </Link>
        }
      />
      <div className="metrics compact">
        <div className="metric">
          <span>Account value</span>
          <strong>{usd(o.equity)}</strong>
          <small>Started with {usd(o.initial_cash)}</small>
        </div>
        <div className="metric">
          <span>Total profit / loss</span>
          <strong
            className={Number(o.cumulative_pnl) >= 0 ? "positive" : "negative"}
          >
            {usd(o.cumulative_pnl)}
          </strong>
          <small>{Number(o.cumulative_return).toFixed(2)}% return</small>
        </div>
        <div className="metric">
          <span>Cash available</span>
          <strong>{usd(o.cash)}</strong>
          <small>{usd(o.invested_value)} invested</small>
        </div>
      </div>
      <Panel title="Holdings">
        {o.positions.length ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Stock</th>
                  <th>Shares</th>
                  <th>Cost</th>
                  <th>Value</th>
                </tr>
              </thead>
              <tbody>
                {o.positions.map((p, i) => (
                  <tr key={i}>
                    <td>
                      <strong>{String(p.ticker)}</strong>
                    </td>
                    <td>{Number(p.quantity).toFixed(4)}</td>
                    <td>{usd(String(p.basis))}</td>
                    <td>{p.value == null ? "—" : usd(String(p.value))}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="empty">No holdings. The firm is holding cash.</p>
        )}
      </Panel>
      <Panel title="Account performance">
        <EquityChart series={o.equity_series} />
      </Panel>
      <div className="bottom-grid">
        <Panel
          title="Recent weeks"
          aside={
            <Link href="/weeks/" className="text-link">
              View all →
            </Link>
          }
        >
          <History weeks={ws.slice(0, 4)} />
        </Panel>
        <Panel title="Latest meeting">
          {ms[0] ? (
            <ArticleCard
              {...ms[0]}
              date={ms[0].sunday}
              minutes={ms[0].reading_minutes}
            />
          ) : (
            <p className="empty">
              The first team discussion is scheduled for Sunday.
            </p>
          )}
        </Panel>
      </div>
      <div className="section-title">
        <h2>The team</h2>
      </div>
      <div className="agent-grid">
        {[
          {
            name: "Avery",
            agent: "researcher_a",
            role: "Company research",
          },
          {
            name: "Morgan",
            agent: "researcher_b",
            role: "Price trends",
          },
          {
            name: "Casey",
            agent: "manager",
            role: "Portfolio manager",
          },
          {
            name: "Riley",
            agent: "analyst",
            role: "Results & lessons",
          },
        ].map((a) => (
          <div className="agent-card" key={a.name}>
            <AgentAvatar agent={a.agent} />
            <h3>{a.name}</h3>
            <span className="role-label">{a.role}</span>
          </div>
        ))}
      </div>
      <div className="schedule-strip">
        <div>
          <strong>Monday</strong>
          <small>Research & buy</small>
        </div>
        <div>
          <strong>Friday</strong>
          <small>Sell & review</small>
        </div>
        <div>
          <strong>Sunday</strong>
          <small>Team discussion</small>
        </div>
      </div>
      <p className="freshness">
        Prices as of{" "}
        {new Date(o.valuation_time).toLocaleString("en-US", {
          timeZone: "America/New_York",
          month: "short",
          day: "numeric",
          hour: "numeric",
          minute: "2-digit",
        })}{" "}
        ET.
      </p>
    </>
  );
}
