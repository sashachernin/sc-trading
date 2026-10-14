"use client";
import { useState } from "react";
import Link from "next/link";
import type { WeekIndex } from "@/lib/data";
import { Badge } from "./ui";
import { Search, ArrowUpRight } from "lucide-react";
export default function History({ weeks }: { weeks: WeekIndex[] }) {
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("ALL");
  const [sort, setSort] = useState("newest");
  const rows = weeks
    .filter(
      (w) =>
        (w.id + " " + w.status).toLowerCase().includes(q.toLowerCase()) &&
        (status === "ALL" || w.status === status),
    )
    .sort((a, b) =>
      sort === "pnl"
        ? Number(b.pnl) - Number(a.pnl)
        : b.monday.localeCompare(a.monday),
    );
  return (
    <>
      {weeks.length > 4 && (
        <div className="filters">
          <label className="search">
            <Search size={16} />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search weeks…"
              aria-label="Search published weeks"
            />
          </label>
          <select
            aria-label="Filter by status"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            <option value="ALL">All statuses</option>
            {[...new Set(weeks.map((w) => w.status))].map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
          <select
            aria-label="Sort weeks"
            value={sort}
            onChange={(e) => setSort(e.target.value)}
          >
            <option value="newest">Newest first</option>
            <option value="pnl">Highest profit</option>
          </select>
        </div>
      )}
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Week of</th>
              <th>Status</th>

              <th>Result</th>
              <th>Review</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((w) => (
              <tr key={w.id}>
                <td>
                  <Link href={`/weeks/${w.id}/`}>{w.monday}</Link>
                </td>
                <td>
                  <Badge status={w.status} />
                </td>

                <td className={Number(w.pnl) >= 0 ? "positive" : "negative"}>
                  {w.pnl === null
                    ? "Pending"
                    : new Intl.NumberFormat("en-US", {
                        style: "currency",
                        currency: "USD",
                      }).format(Number(w.pnl))}
                </td>
                <td>{w.review_available ? "Published" : "Pending"}</td>
                <td>
                  <Link
                    href={`/weeks/${w.id}/`}
                    aria-label={`Read week ${w.monday}`}
                  >
                    <ArrowUpRight size={16} />
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!rows.length && <p className="empty">No weeks yet.</p>}
      </div>
    </>
  );
}
