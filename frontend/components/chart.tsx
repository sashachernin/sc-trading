"use client";
import { useState } from "react";
import type { Overview } from "@/lib/data";
export default function EquityChart({
  series,
}: {
  series: Overview["equity_series"];
}) {
  const [selected, setSelected] = useState(series.length - 1);
  const [view, setView] = useState<"equity" | "drawdown">("equity");
  const all = series.flatMap((s) =>
    view === "equity"
      ? [Number(s.equity), Number(s.benchmark_equity)]
      : [Number(s.drawdown)],
  );
  const min = Math.min(...all) - (view === "equity" ? 10 : 1);
  const max = Math.max(...all) + (view === "equity" ? 10 : 1);
  const x = (i: number) => 50 + (i * 700) / Math.max(1, series.length - 1);
  const y = (v: number) => 190 - ((v - min) / (max - min)) * 155;
  const pts = series
    .map(
      (s, i) =>
        `${x(i)},${y(Number(view === "equity" ? s.equity : s.drawdown))}`,
    )
    .join(" ");
  return (
    <>
      <div className="chart-controls">
        <div className="legend">
          <span className="dot" />
          Paper account
          {view === "equity" && (
            <>
              <span className="dot gray" />
              SPY comparison
            </>
          )}
        </div>
        <div className="segmented">
          <button
            aria-pressed={view === "equity"}
            onClick={() => setView("equity")}
          >
            Equity
          </button>
          <button
            aria-pressed={view === "drawdown"}
            onClick={() => setView("drawdown")}
          >
            Drawdown
          </button>
        </div>
      </div>
      <div className="chart-value">
        <strong>
          {view === "equity"
            ? `$${Number(series[selected].equity).toFixed(2)}`
            : `${Number(series[selected].drawdown).toFixed(2)}%`}
        </strong>
        <span>{series[selected].date} · PAPER / SIMULATED</span>
      </div>
      <svg
        className="chart"
        viewBox="0 0 800 225"
        role="img"
        aria-label="Interactive paper account equity and comparison chart"
      >
        <defs>
          <linearGradient id="chart-fill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#278568" stopOpacity=".18" />
            <stop offset="100%" stopColor="#278568" stopOpacity="0" />
          </linearGradient>
        </defs>
        {[0, 1, 2, 3].map((i) => {
          const value = min + ((max - min) * i) / 3;
          return (
            <g key={i}>
              <line
                x1="50"
                x2="750"
                y1={y(value)}
                y2={y(value)}
                stroke="#e8ece8"
                strokeDasharray="4 4"
              />
              <text x="0" y={y(value) + 4} fontSize="10" fill="#829087">
                {view === "equity"
                  ? `$${Math.round(value)}`
                  : `${value.toFixed(1)}%`}
              </text>
            </g>
          );
        })}
        <polygon
          points={`50,195 ${pts} ${x(series.length - 1)},195`}
          fill="url(#chart-fill)"
        />
        {view === "equity" && (
          <polyline
            points={series
              .map((s, i) => `${x(i)},${y(Number(s.benchmark_equity))}`)
              .join(" ")}
            stroke="#b0bab3"
            strokeWidth="2"
            strokeDasharray="5 5"
            fill="none"
          />
        )}
        <polyline points={pts} fill="none" stroke="#278568" strokeWidth="2.5" />
        {series.map((s, i) => (
          <g key={i} onMouseEnter={() => setSelected(i)}>
            <circle
              cx={x(i)}
              cy={y(Number(view === "equity" ? s.equity : s.drawdown))}
              r={selected === i ? 5 : 3}
              fill="#fff"
              stroke="#278568"
              strokeWidth="2"
            />
            <text
              x={x(i)}
              y="217"
              textAnchor="middle"
              fontSize="10"
              fill="#829087"
            >
              {s.date.slice(5)}
            </text>
          </g>
        ))}
      </svg>
      <div className="chart-dates" aria-label="Select chart observation">
        {series.map((s, i) => (
          <button
            key={i}
            onClick={() => setSelected(i)}
            aria-pressed={selected === i}
          >
            {s.date}
          </button>
        ))}
      </div>
    </>
  );
}
