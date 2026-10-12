import type { Metadata } from "next";
import Link from "next/link";
import {
  FlaskConical,
  LayoutDashboard,
  CalendarRange,
  MessagesSquare,
  BookOpen,
  Activity,
  ArrowUpRight,
} from "lucide-react";
import { manifest } from "@/lib/data";
import "./globals.css";
export const metadata: Metadata = {
  title: "AI Investment Lab · Paper research",
  description: "A read-only record of a bounded AI paper-trading experiment.",
};
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const m = manifest();
  return (
    <html lang="en">
      <body>
        <div className="shell">
          <aside className="sidebar">
            <Link href="/" className="brand">
              <span className="brand-icon">
                <FlaskConical size={23} />
              </span>
              <span>
                Investment Lab<small>AN AUTONOMOUS EXPERIMENT</small>
              </span>
            </Link>
            <div className="nav-label">RESEARCH WORKSPACE</div>
            <nav aria-label="Main navigation">
              {[
                ["/", "Overview", LayoutDashboard],
                ["/weeks/", "Weekly research", CalendarRange],
                ["/meetings/", "Team meetings", MessagesSquare],
                ["/learning/", "Learning journal", BookOpen],
                ["/operations/", "Operations", Activity],
              ].map(([href, label, Icon]) => {
                const Component = Icon as typeof Activity;
                return (
                  <Link href={href as string} key={href as string}>
                    <Component size={18} />
                    {label as string}
                  </Link>
                );
              })}
            </nav>
            <div className="sidebar-note">
              <span className="dot" /> Paper research only
              <p>
                Four perspectives.
                <br />
                One transparent experiment.
              </p>
              <a href="/data/manifest.json">
                Snapshot manifest <ArrowUpRight size={14} />
              </a>
            </div>
            <div className="sidebar-bottom">
              <span className="avatar">IL</span>
              <span>
                AI Investment Lab<small>Read-only workspace</small>
              </span>
            </div>
          </aside>
          <div className="workspace">
            <header className="topbar">
              <span>
                WORKSPACE <span className="slash">/</span>{" "}
                <strong>Investment Lab</strong>
              </span>
              <div className="top-status">
                <span className="badge paper">PAPER / SIMULATED</span>
                <span className="badge">
                  {m.synthetic ? "Synthetic demonstration" : "Forward research"}
                </span>
              </div>
            </header>
            <nav className="mobile-nav" aria-label="Mobile navigation">
              <Link href="/">Overview</Link>
              <Link href="/weeks/">Research</Link>
              <Link href="/meetings/">Meetings</Link>
              <Link href="/learning/">Learning</Link>
              <Link href="/operations/">Operations</Link>
            </nav>
            <main>{children}</main>
            <footer>
              <span>
                Published {new Date(m.created_at).toUTCString()} ·{" "}
                {m.snapshot_id}
              </span>
              <span>USD · America/New_York · Read-only snapshot</span>
            </footer>
          </div>
        </div>
      </body>
    </html>
  );
}
