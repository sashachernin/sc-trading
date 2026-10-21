import fs from "node:fs";
import path from "node:path";
import { z } from "zod";
const decimal = z.string().regex(/^-?\d+(\.\d+)?([eE][+-]?\d+)?$/);
export const manifestSchema = z
  .object({
    schema_version: z.literal("1"),
    snapshot_id: z.string(),
    source_revision: z.number(),
    experiment_id: z.string(),
    label: z.literal("PAPER / SIMULATED"),
    synthetic: z.boolean(),
    created_at: z.string(),
    source_cutoff: z.string(),
    valuation_time: z.string(),
    next_expected_publication: z.string(),
    files: z.array(
      z.object({
        path: z.string(),
        sha256: z.string(),
        bytes: z.number(),
        schema_version: z.literal("1"),
      }),
    ),
  })
  .strict();
export const overviewSchema = z
  .object({
    label: z.literal("PAPER / SIMULATED"),
    currency: z.literal("USD"),
    initial_cash: decimal,
    equity: decimal,
    cash: decimal,
    invested_value: decimal,
    realized_pnl: decimal,
    unrealized_pnl: decimal,
    cumulative_pnl: decimal,
    cumulative_return: decimal,
    monthly_pnl: decimal,
    rolling_four_week_pnl: decimal,
    target_monthly_profit: z.literal("100.00"),
    target_is_experimental: z.literal(true),
    completed_cycles: z.number(),
    skipped_cycles: z.number(),
    valuation_time: z.string(),
    equity_series: z.array(
      z.object({
        week: z.string(),
        date: z.string(),
        equity: decimal,
        pnl: decimal,
        benchmark_equity: decimal.nullable(),
        drawdown: decimal,
      }),
    ),
    positions: z.array(z.record(z.string(), z.unknown())),
    fills: z.array(z.record(z.string(), z.unknown())),
    latest_meeting: z.string().nullable(),
  })
  .strict();
export type Overview = z.infer<typeof overviewSchema>;
export type WeekIndex = {
  id: string;
  monday: string;
  status: string;
  pnl: string | null;
  proposal_count: number;
  review_available: boolean;
};
export type Proposal = {
  id: string;
  run_id: string;
  role: string;
  ticker: string;
  company: string;
  rank: number;
  max_allocation: string;
  expected_return: number;
  downside: number;
  probability_profit: number;
  confidence: number;
  thesis: string;
  catalysts: string[];
  risks: string[];
  invalidation: string;
  assumptions: string[];
  evidence_ids: string[];
};
export type Week = {
  id: string;
  monday: string;
  status: string;
  label: string;
  data: {
    pnl?: string;
    reason?: string;
    starting_equity?: string;
    current_equity?: string;
    current_pnl?: string;
    ending_equity?: string;
    risk_checks?: string[];
    benchmark_return?: string;
    comparisons?: {
      ticker: string;
      expected_return: number;
      observed_return: number;
      proposal_id: string;
    }[];
    review_status?: string;
  };
  proposals: Proposal[];
  fills?: import("@/components/execution").PaperFill[];
  decision: {
    allocations: {
      proposal_id: string;
      amount: string;
      percent: string;
      rationale: string;
    }[];
    rejections: { proposal_id: string; rationale: string }[];
    retained_cash: string;
    summary: string;
    uncertainty: string;
  } | null;
  review: {
    summary: string;
    scorecards: { role: string; score: number; assessment: string }[];
    forecast_comparisons: string[];
    selected_vs_rejected: string;
    execution_effects: string;
    limitations: string;
    successes: string[];
    weaknesses: string[];
    error_categories: string[];
  } | null;
  runs: {
    id: string;
    role: string;
    purpose: string;
    status: string;
    model: string;
    manifest: Record<string, unknown>;
    prompt_excerpt: string;
    research_summary?: string;
    abstention_reason?: string | null;
    investigated_tickers?: string[];
    web_search_mode?: string;
    web_activity?: { completed_calls: number };
    sources?: {
      id: string;
      url: string;
      title: string;
      published_at: string | null;
      finding: string;
    }[];
  }[];
  timeline: { stage: string; completed_at: string }[];
  meeting_ids: string[];
  snapshots: unknown[];
};
export type MeetingIndex = {
  id: string;
  sunday: string;
  title: string;
  excerpt: string;
  status: string;
  week_id: string | null;
  participants: { name: string; role: string }[];
  reading_minutes: number;
};
export type Meeting = MeetingIndex & {
  context: {
    ceo_message?: { author: string; sunday: string; message_markdown: string; sha256: string } | null;
    cutoff: string;
    source: { pnl: string; status: string; cash: string };
  };
  upcoming_monday: string;
  data: {
    title: string;
    standfirst: string;
    recap: string;
    takeaways: string[];
    focus_areas: string[];
    open_questions: string[];
    generated_at: string;
    synthetic: boolean;
    unavailable: string[];
  };
  turns: {
    id: string;
    run_id: string;
    sequence: number;
    speaker: string;
    phase: string;
    message_markdown: string;
    reply_to_turn_ids: string[];
    evidence_ids: string[];
    provenance: Record<string, unknown>;
  }[];
};
export type Lesson = {
  id: string;
  role: string;
  status: string;
  version: number;
  week_id: string;
  text: string;
  confidence: number;
  expiry: string;
  operation: string;
  evidence_ids: string[];
  expected_effect: string;
  success_metric: string;
  rollback_condition: string;
  mode: string;
  validation_errors: string[];
};
export type Operations = {
  observed_at: string;
  paused: boolean;
  worker_status: string;
  queue: Record<string, number>;
  incidents: {
    id: string;
    category: string;
    summary: string;
    observed_at: string;
  }[];
  audit: { action: string; data: unknown; created_at: string }[];
  settings: {
    provider: string;
    synthetic: boolean;
    learning_mode: string;
    site_visibility: string;
    private_access_verified: boolean;
    max_stock_allocation: string;
    max_deployed: string;
    start: string;
    end: string;
    participants: Record<string, { name: string; role: string }>;
    schedule: Record<string, string>;
    meeting_turn_limit: number;
    active_memory_cap: number;
    models: Record<string, string>;
  };
  previous_delivery: { snapshot_id: string; status: string } | null;
};
function read<T>(file: string): T {
  return JSON.parse(
    fs.readFileSync(path.join(process.cwd(), "public/data", file), "utf8"),
  ) as T;
}
export function manifest() {
  return manifestSchema.parse(read("manifest.json"));
}
export function overview() {
  return overviewSchema.parse(read("overview.json"));
}
export const weeks = () => read<WeekIndex[]>("weeks/index.json");
export const week = (id: string) => read<Week>(`weeks/${id}.json`);
export const meetings = () => read<MeetingIndex[]>("meetings/index.json");
export const meeting = (id: string) => read<Meeting>(`meetings/${id}.json`);
export const lessons = () => read<Lesson[]>("learning/index.json");
export const operations = () => read<Operations>("operations.json");
export function usd(value: string | number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(Number(value));
}
export function percent(value: string | number) {
  return `${(Number(value) * 100).toFixed(1)}%`;
}
export const names: Record<
  string,
  { name: string; role: string; avatar: string; color: string }
> = {
  researcher_a: {
    name: "Avery",
    role: "Fundamentals & catalysts",
    avatar: "/images/agents/avery.png",
    color: "sage",
  },
  researcher_b: {
    name: "Morgan",
    role: "Momentum & price",
    avatar: "/images/agents/morgan.png",
    color: "blue",
  },
  manager: {
    name: "Casey",
    role: "Portfolio manager",
    avatar: "/images/agents/casey.png",
    color: "sand",
  },
  analyst: {
    name: "Riley",
    role: "Research analyst",
    avatar: "/images/agents/riley.png",
    color: "rose",
  },
};
