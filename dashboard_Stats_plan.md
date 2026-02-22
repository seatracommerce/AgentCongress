 Plan: Analytics/Stats Dashboard                                                                                                                                                                                                                                                                                                                                      

 Context

 The app simulates congressional debates and tracks real-world vote outcomes, but there is no dashboard to see aggregate performance over time. This plan adds a /stats page showing daily simulation volumes (passed/failed), daily real-world vote counts, and an AI accuracy breakdown comparing simulation results against actual congressional outcomes.

 ---
 Files to Create

 backend/schemas/stats.py

 Four Pydantic models:
 class DailySimStat(BaseModel):
     date: str; total: int; passed: int; failed: int

 class DailyRealStat(BaseModel):
     date: str; total: int; passed: int; failed: int

 class ComparisonTotals(BaseModel):
     both_passed: int; both_failed: int
     sim_passed_real_failed: int; sim_failed_real_passed: int; no_real_vote: int

 class StatsResponse(BaseModel):
     sim_daily: list[DailySimStat]
     real_daily: list[DailyRealStat]
     comparison: ComparisonTotals

 backend/api/stats.py

 APIRouter with single GET "" endpoint (/stats) using 3 async queries:

 1. Simulation daily: GROUP BY cast(Debate.completed_at, Date) where status='completed' + result IS NOT NULL; case() sums passed/failed counts.
 2. Real-world daily: GROUP BY cast(Bill.real_vote_date, Date) where real_vote_date IS NOT NULL; normalizes "passed"|"voice_vote_passed" → passed, "failed"|"voice_vote_failed" → failed via case().
 3. Comparison: JOIN Debate ⟶ Bill on bill_id; case() normalizes real result; Python loop tallies both_passed, both_failed, sim_passed_real_failed, sim_failed_real_passed, no_real_vote.

 Follows exact pattern from backend/api/debates.py (APIRouter, Depends(get_db), AsyncSession).

 frontend/app/stats/page.tsx

 Server component (export const revalidate = 60). Sections:
 - Summary stat cards (grid 2×2 sm:4): total debates, sim passed, sim failed, real votes tracked
 - AI vs Real Congress comparison grid (3 cols): green cards for matches, orange for diverge, gray for "awaiting real vote"
 - Side-by-side daily bar charts (lg:grid-cols-2): simulation results by day + real votes by day

 CSS bar chart (DailyBar) reuses the flex rounded-full overflow-hidden + style={{ width: \${pct}%` }}pattern fromVoteBoard.tsx. Shows count inside bar when pct > 12`.

 Date formatted as "Feb 22" using new Date(d + "T00:00:00").toLocaleDateString(...) (appending time avoids UTC-offset day-shift bug).

 ---
 Files to Modify

 backend/schemas/__init__.py

 Add import + export of StatsResponse (and related models).

 backend/main.py

 from backend.api.stats import router as stats_router
 app.include_router(stats_router, prefix="/stats", tags=["stats"])
 Insert after the existing three include_router calls (line 44).

 frontend/lib/api.ts

 Append four TS interfaces (DailySimStat, DailyRealStat, ComparisonTotals, StatsResponse) and:
 export const fetchStats = () => apiFetch<StatsResponse>("/stats");

 frontend/app/layout.tsx

 Add <nav> with "Debates" + "Stats" links inside the header flex div, after the subtitle <span>:
 <nav className="ml-auto flex items-center gap-4 text-sm">
   <a href="/" className="text-gray-600 hover:text-blue-700 font-medium">Debates</a>
   <a href="/stats" className="text-gray-600 hover:text-blue-700 font-medium">Stats</a>
 </nav>

 ---
 Implementation Order

 1. backend/schemas/stats.py (new)
 2. backend/schemas/__init__.py (add exports)
 3. backend/api/stats.py (new)
 4. backend/main.py (register router)
 5. frontend/lib/api.ts (append types + fetch)
 6. frontend/app/stats/page.tsx (new)
 7. frontend/app/layout.tsx (add nav)

 ---
 Verification

 1. uvicorn backend.main:app --reload --port 8000 → GET http://localhost:8000/stats returns JSON with sim_daily, real_daily, comparison.
 2. cd frontend && npm run dev → navigate to http://localhost:3000/stats, see the dashboard.
 3. Header "Stats" link works; "Debates" link returns to home.
 4. With no data: empty-state messages show ("No data yet." / "No comparison data yet.").
 5. Run existing tests: pytest tests/ — no regressions expected (no existing routes modified).