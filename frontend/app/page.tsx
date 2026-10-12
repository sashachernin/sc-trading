import Link from "next/link";
import {
  ArrowUpRight,
  ArrowRight,
  TrendingUp,
  Wallet,
  Target,
  CalendarDays,
  MessagesSquare,
} from "lucide-react";
import { overview, manifest, weeks, meetings, lessons, usd } from "@/lib/data";
import { Heading, Panel, Badge, ArticleCard } from "@/components/ui";
import EquityChart from "@/components/chart";
import History from "@/components/history";
export default function Home() {
  const o = overview(),
    m = manifest(),
    ws = weeks(),
    ms = meetings(),
    ls = lessons();
  const active = ls.filter((l) => l.status === "ACTIVE");
  return (
    <>
      <Heading
        eyebrow="THE EXPERIMENT · YEAR ONE"
        title="Small capital. Open questions."
        description="A transparent record of four AI agents learning to invest, one paper-trading week at a time."
        action={
          <Link className="button" href="/weeks/">
            Explore the research <ArrowUpRight size={16} />
          </Link>
        }
      />
      <div className="notice">
        <span className="dot" />
        <span>
          {m.synthetic
            ? "Synthetic demonstration — prices, model outputs, and outcomes are test fixtures."
            : "Forward paper research — outcomes are simulated."}{" "}
          <strong>No live money is traded.</strong>
        </span>
        <span className="notice-date">
          Valued {o.valuation_time.slice(0, 10)}
        </span>
      </div>
      <div className="metrics">
        <div className="metric">
          <span>
            Account equity <Wallet size={17} />
          </span>
          <strong>{usd(o.equity)}</strong>
          <small>From {usd(o.initial_cash)} starting capital</small>
        </div>
        <div className="metric">
          <span>
            Since inception <TrendingUp size={17} />
          </span>
          <strong
            className={Number(o.cumulative_pnl) >= 0 ? "positive" : "negative"}
          >
            {Number(o.cumulative_pnl) >= 0 ? "+" : ""}
            {usd(o.cumulative_pnl)}
          </strong>
          <small>
            {Number(o.cumulative_return).toFixed(2)}% cumulative paper return
          </small>
        </div>
        <div className="metric">
          <span>
            This calendar month <CalendarDays size={17} />
          </span>
          <strong>{usd(o.monthly_pnl)}</strong>
          <small>
            Realized net paper profit · {o.valuation_time.slice(0, 7)}
          </small>
        </div>
        <div className="metric">
          <span>
            Month 12 research target <Target size={17} />
          </span>
          <strong>
            $100 <em>/ month</em>
          </strong>
          <small>Experimental objective · outcome uncertain</small>
        </div>
      </div>
      <div className="overview-grid">
        <Panel
          title="The account, over time"
          aside={<span className="subtle">USD · net of modeled costs</span>}
        >
          <EquityChart series={o.equity_series} />
        </Panel>
        <Panel title="Inside the account">
          <div className="cash-ring">
            <svg viewBox="0 0 160 160" aria-label="Paper cash allocation">
              <circle
                cx="80"
                cy="80"
                r="61"
                fill="none"
                stroke="#eef1eb"
                strokeWidth="12"
              />
              <circle
                cx="80"
                cy="80"
                r="61"
                fill="none"
                stroke="#2e8268"
                strokeWidth="12"
                strokeDasharray={`${(Number(o.cash) / Number(o.equity)) * 383} 383`}
                transform="rotate(-90 80 80)"
              />
            </svg>
            <div>
              <strong>
                {((Number(o.cash) / Number(o.equity)) * 100).toFixed(0)}%
              </strong>
              <span>held in cash</span>
            </div>
          </div>
          <div className="account-line">
            <span>
              <i className="dot" />
              Cash available
            </span>
            <strong>{usd(o.cash)}</strong>
          </div>
          <div className="account-line">
            <span>
              <i className="dot gray" />
              Invested value
            </span>
            <strong>{usd(o.invested_value)}</strong>
          </div>
          <div className="account-line">
            <span>Realized / unrealized P&L</span>
            <strong>
              {usd(o.realized_pnl)} / {usd(o.unrealized_pnl)}
            </strong>
          </div>
          <div className="mini-note">
            Long-only · cash-funded · fractional shares
            <br />
            40% ticker cap · 95% deployment cap
          </div>
        </Panel>
      </div>
      <div className="section-title">
        <h2>Four agents. A shared feedback loop.</h2>
        <Link href="/learning/">
          Learning journal <ArrowRight size={15} />
        </Link>
      </div>
      <div className="agent-grid">
        {[
          {
            name: "Avery",
            initials: "AV",
            role: "Fundamentals & catalysts",
            code: "researcher_a",
            description: "What could change a company’s value this week?",
            color: "sage",
          },
          {
            name: "Morgan",
            initials: "MO",
            role: "Momentum & price",
            code: "researcher_b",
            description: "What does price behavior tell us — and leave out?",
            color: "blue",
          },
          {
            name: "Casey",
            initials: "CA",
            role: "Portfolio manager",
            code: "manager",
            description: "Which ideas deserve capital, and how much?",
            color: "sand",
          },
          {
            name: "Riley",
            initials: "RI",
            role: "Research analyst",
            code: "analyst",
            description: "What happened, and what should we learn?",
            color: "rose",
          },
        ].map((a) => (
          <div className="agent-card" key={a.code}>
            <span className={`avatar ${a.color}`}>{a.initials}</span>
            <h3>{a.name}</h3>
            <span className="role-label">{a.role}</span>
            <p>{a.description}</p>
            <div>
              {a.code === "analyst"
                ? "Reviews reconciled outcomes"
                : `${active.filter((l) => l.role === a.code).length} active research lessons`}
              <span className="dot" />
            </div>
          </div>
        ))}
      </div>
      <div className="bottom-grid">
        <Panel
          title="Recent weekly research"
          aside={
            <Link href="/weeks/" className="text-link">
              View all <ArrowUpRight size={15} />
            </Link>
          }
        >
          <History weeks={ws.slice(0, 4)} />
        </Panel>
        <section>
          <div className="panel-heading standalone">
            <h2>From the Sunday table</h2>
            <MessagesSquare size={19} />
          </div>
          {ms[0] ? (
            <ArticleCard
              {...ms[0]}
              date={ms[0].sunday}
              minutes={ms[0].reading_minutes}
            />
          ) : (
            <p className="empty">No meeting has been published.</p>
          )}
        </section>
      </div>
      <Panel title="Current paper positions">
        <div className="table-scroll">
          {o.positions.length ? (
            <table>
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Shares</th>
                  <th>Basis (USD)</th>
                  <th>Observed value (USD)</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {o.positions.map((p, i) => (
                  <tr key={i}>
                    <td>{String(p.ticker)}</td>
                    <td>{String(p.quantity)}</td>
                    <td>{String(p.basis)}</td>
                    <td>{String(p.value)}</td>
                    <td>{String(p.status)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="subtle">
              No open paper positions at this valuation. The account is holding
              cash.
            </p>
          )}
        </div>
      </Panel>
      <div className="schedule-strip">
        <div>
          <span className="eyebrow">THE WEEKLY RHYTHM</span>
          <p>Planned schedule · America/New_York</p>
        </div>
        <div>
          <strong>
            MON <span>09:35</span>
          </strong>
          <small>Independent research & paper entry</small>
        </div>
        <ArrowRight size={18} />
        <div>
          <strong>
            FRI <span>15:45</span>
          </strong>
          <small>Liquidation, review & bounded learning</small>
        </div>
        <ArrowRight size={18} />
        <div>
          <strong>
            SUN <span>12:00</span>
          </strong>
          <small>Manager-led team discussion</small>
        </div>
      </div>
      <p className="freshness">
        This page shows published observations, not live prices or service
        health. A reload reads this snapshot. No newer snapshot has been
        published since {new Date(m.created_at).toUTCString()}.
      </p>
    </>
  );
}
