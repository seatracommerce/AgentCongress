const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface Bill {
  id: number;
  congress_bill_id: string;
  title: string;
  chamber: string | null;
  status: string | null;
  sponsor: string | null;
  bill_type: string | null;
  congress_number: number | null;
  introduced_date: string | null;
  last_action_date: string | null;
  last_action_text: string | null;
  congress_url: string | null;
  real_vote_result: string | null;
  real_vote_yea: number | null;
  real_vote_nay: number | null;
  real_vote_date: string | null;
  real_vote_description: string | null;
  importance_score: number;
  debate_triggered: boolean;
  created_at: string;
  summary?: string | null;
  debate_id?: number | null;
}

export interface Statement {
  id: number;
  debate_id: number;
  caucus_id: string;
  turn_type: "opening" | "debate" | "closing";
  content: string;
  sequence: number;
  created_at: string;
}

export interface Vote {
  id: number;
  debate_id: number;
  caucus_id: string;
  choice: "yea" | "nay" | "present";
  rationale: string | null;
  weighted_seats: number;
  created_at: string;
}

export interface Debate {
  id: number;
  bill_id: number;
  status: string;
  summary: string | null;
  yea_seats: number | null;
  nay_seats: number | null;
  present_seats: number | null;
  result: string | null;
  chamber: string | null;
  started_at: string | null;
  completed_at: string | null;
  published_to_x_at: string | null;
  created_at: string;
  statements?: Statement[];
  votes?: Vote[];
}

export interface PagedResponse<T> {
  total: number;
  page: number;
  page_size: number;
  items: T[];
}

export interface DailySimStat {
  date: string;
  total: number;
  passed: number;
  failed: number;
}

export interface DailyRealStat {
  date: string;
  total: number;
  passed: number;
  failed: number;
}

export interface ComparisonTotals {
  both_passed: number;
  both_failed: number;
  sim_passed_real_failed: number;
  sim_failed_real_passed: number;
  no_real_vote: number;
}

export interface StatsResponse {
  sim_daily: DailySimStat[];
  real_daily: DailyRealStat[];
  comparison: ComparisonTotals;
}

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { next: { revalidate: 60 } });
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`);
  return res.json();
}

export const fetchDebates = (page = 1) =>
  apiFetch<PagedResponse<Debate>>(`/debates?page=${page}&page_size=20`);

export const fetchDebate = (id: number) =>
  apiFetch<Debate>(`/debates/${id}`);

export const fetchBill = (id: number) =>
  apiFetch<Bill>(`/bills/${id}`);

export const fetchStats = () => apiFetch<StatsResponse>("/stats");
