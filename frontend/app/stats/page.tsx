import { fetchStats } from "@/lib/api";
import type { DailySimStat, DailyRealStat } from "@/lib/api";

export const dynamic = "force-dynamic";
export const revalidate = 60;

function formatChartDate(d: string) {
  return new Date(d + "T00:00:00Z").toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
}

function DailyBar({
  passed,
  failed,
  total,
  label,
}: {
  passed: number;
  failed: number;
  total: number;
  label: string;
}) {
  if (total === 0) return null;
  const pctPassed = (passed / total) * 100;
  const pctFailed = (failed / total) * 100;
  return (
    <div className="flex items-center gap-2">
      <span className="w-16 text-xs text-gray-500 shrink-0">{label}</span>
      <div className="flex flex-1 rounded-full overflow-hidden h-5 bg-gray-100">
        {pctPassed > 0 && (
          <div
            className="bg-green-500 flex items-center justify-center text-white text-xs font-medium min-w-0"
            style={{ width: `${pctPassed}%` }}
          >
            {pctPassed > 12 ? passed : ""}
          </div>
        )}
        {pctFailed > 0 && (
          <div
            className="bg-red-500 flex items-center justify-center text-white text-xs font-medium min-w-0"
            style={{ width: `${pctFailed}%` }}
          >
            {pctFailed > 12 ? failed : ""}
          </div>
        )}
      </div>
      <span className="text-xs text-gray-400 w-12 shrink-0">{total}</span>
    </div>
  );
}

export default async function StatsPage() {
  const data = await fetchStats();

  const totalDebates = data.sim_daily.reduce((s, d) => s + d.total, 0);
  const simPassed = data.sim_daily.reduce((s, d) => s + d.passed, 0);
  const simFailed = data.sim_daily.reduce((s, d) => s + d.failed, 0);
  const realVotesTracked =
    data.comparison.both_passed +
    data.comparison.both_failed +
    data.comparison.sim_passed_real_failed +
    data.comparison.sim_failed_real_passed;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Stats</h1>
        <p className="text-sm text-gray-500 mt-1">
          Simulation volume and AI vs real Congress comparison
        </p>
      </div>

      {/* Summary stat cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-gray-400">
            Total debates
          </p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{totalDebates}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-gray-400">
            Sim passed
          </p>
          <p className="text-2xl font-bold text-green-700 mt-1">{simPassed}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-gray-400">
            Sim failed
          </p>
          <p className="text-2xl font-bold text-red-700 mt-1">{simFailed}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-gray-400">
            Real votes tracked
          </p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{realVotesTracked}</p>
        </div>
      </div>

      {/* AI vs Real Congress comparison */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-lg font-bold text-gray-900 mb-4">
          AI vs Real Congress
        </h2>
        {data.comparison.both_passed === 0 &&
        data.comparison.both_failed === 0 &&
        data.comparison.sim_passed_real_failed === 0 &&
        data.comparison.sim_failed_real_passed === 0 &&
        data.comparison.no_real_vote === 0 ? (
          <p className="text-sm text-gray-500">No comparison data yet.</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <p className="text-xs font-medium uppercase text-green-700">
                Both passed
              </p>
              <p className="text-2xl font-bold text-green-800">
                {data.comparison.both_passed}
              </p>
            </div>
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <p className="text-xs font-medium uppercase text-green-700">
                Both failed
              </p>
              <p className="text-2xl font-bold text-green-800">
                {data.comparison.both_failed}
              </p>
            </div>
            <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
              <p className="text-xs font-medium uppercase text-orange-700">
                Sim passed, real failed
              </p>
              <p className="text-2xl font-bold text-orange-800">
                {data.comparison.sim_passed_real_failed}
              </p>
            </div>
            <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
              <p className="text-xs font-medium uppercase text-orange-700">
                Sim failed, real passed
              </p>
              <p className="text-2xl font-bold text-orange-800">
                {data.comparison.sim_failed_real_passed}
              </p>
            </div>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
              <p className="text-xs font-medium uppercase text-gray-600">
                Awaiting real vote
              </p>
              <p className="text-2xl font-bold text-gray-800">
                {data.comparison.no_real_vote}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Daily bar charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-bold text-gray-900 mb-4">
            Simulation results by day
          </h2>
          {data.sim_daily.length === 0 ? (
            <p className="text-sm text-gray-500">No data yet.</p>
          ) : (
            <div className="space-y-3">
              {data.sim_daily.slice(0, 14).map((d: DailySimStat) => (
                <DailyBar
                  key={d.date}
                  label={formatChartDate(d.date)}
                  passed={d.passed}
                  failed={d.failed}
                  total={d.total}
                />
              ))}
            </div>
          )}
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-bold text-gray-900 mb-4">
            Real votes by day
          </h2>
          {data.real_daily.length === 0 ? (
            <p className="text-sm text-gray-500">No data yet.</p>
          ) : (
            <div className="space-y-3">
              {data.real_daily.slice(0, 14).map((d: DailyRealStat) => (
                <DailyBar
                  key={d.date}
                  label={formatChartDate(d.date)}
                  passed={d.passed}
                  failed={d.failed}
                  total={d.total}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
