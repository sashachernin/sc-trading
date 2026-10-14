"use client";
import { useState } from "react";
import type { MeetingIndex } from "@/lib/data";
import { ArticleCard } from "./ui";
export default function Archive({ items }: { items: MeetingIndex[] }) {
  const [page, setPage] = useState(0);
  return (
    <>
      <div className="article-grid">
        {items.slice(page * 6, page * 6 + 6).map((m) => (
          <ArticleCard
            key={m.id}
            {...m}
            date={m.sunday}
            minutes={m.reading_minutes}
          />
        ))}
      </div>
      {!items.length && (
        <p className="empty">
          The first team discussion is scheduled for Sunday.
        </p>
      )}
      {items.length > 6 && (
        <div className="pagination">
          <button disabled={page === 0} onClick={() => setPage(page - 1)}>
            Previous
          </button>
          <span>
            Page {page + 1} of {Math.max(1, Math.ceil(items.length / 6))}
          </span>
          <button
            disabled={(page + 1) * 6 >= items.length}
            onClick={() => setPage(page + 1)}
          >
            Next
          </button>
        </div>
      )}
    </>
  );
}
