import type { Metadata } from "next";
import Link from "next/link";
import { ChartNoAxesCombined } from "lucide-react";
import Navigation from "@/components/navigation";
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
        <a className="skip-link" href="#main-content">
          Skip to content
        </a>
        <div className="shell">
          <aside className="sidebar">
            <Link href="/" className="brand" aria-label="AI Trading Firm home">
              <span className="brand-icon">
                <ChartNoAxesCombined size={23} />
              </span>
              <span className="brand-name">AI Trading Firm</span>
            </Link>

            <div className="nav-label">WORKSPACE</div>
            <Navigation />
          </aside>
          <div className="workspace">
            <header className="topbar">
              <div className="topbar-brand">
                <img
                  className="spglobal-logo"
                  src="/images/brand/sp-global.svg"
                  alt="S&P Global"
                  width={151}
                  height={33}
                />
                <span className="topbar-title">
                  <strong>AI Trading Firm</strong>
                </span>
              </div>
              <span className="badge paper">Simulated account</span>
            </header>
            <Navigation mobile />
            <main id="main-content" tabIndex={-1}>
              {children}
            </main>
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
