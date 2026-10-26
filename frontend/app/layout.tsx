import type { Metadata } from "next";
import Link from "next/link";
import {
  FlaskConical,
  LayoutDashboard,
  CalendarRange,
  BookOpen,
  Activity,
} from "lucide-react";
import { manifest } from "@/lib/data";
import "./globals.css";
export const metadata: Metadata = {
  title: "AI Trading Firm",
  description: "The firm’s decisions, holdings and results.",
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
              <span>AI Trading Firm</span>
            </Link>

            <nav aria-label="Main navigation">
              {[
                ["/", "Overview", LayoutDashboard],
                ["/weeks/", "Weeks", CalendarRange],
                ["/learning/", "Learning", BookOpen],
                ["/operations/", "Status", Activity],
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
          </aside>
          <div className="workspace">
            <header className="topbar">
              <span>
                <strong>AI Trading Firm</strong>
              </span>
            </header>
            <nav className="mobile-nav" aria-label="Mobile navigation">
              <Link href="/">Overview</Link>
              <Link href="/weeks/">Weeks</Link>
              <Link href="/learning/">Learning</Link>
              <Link href="/operations/">Status</Link>
            </nav>
            <main>{children}</main>
            <footer>
              <span>
                Updated{" "}
                {new Date(m.created_at).toLocaleString("en-US", {
                  timeZone: "America/New_York",
                  month: "short",
                  day: "numeric",
                  hour: "numeric",
                  minute: "2-digit",
                })}{" "}
                ET
              </span>
              <span>Simulated account</span>
            </footer>
          </div>
        </div>
      </body>
    </html>
  );
}
