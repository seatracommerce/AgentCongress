import type { Vote } from "@/lib/api";

const CAUCUS_META: Record<string, { name: string; color: string }> = {
  progressive: { name: "Progressive Caucus", color: "#7C3AED" },
  new_dem: { name: "New Democrat Coalition", color: "#2563EB" },
  rsc: { name: "Republican Study Committee", color: "#DC2626" },
  freedom: { name: "House Freedom Caucus", color: "#991B1B" },
  problem_solvers: { name: "Problem Solvers Caucus", color: "#16A34A" },
  cbc: { name: "Congressional Black Caucus", color: "#D97706" },
  armed_services: { name: "Armed Services Bloc", color: "#475569" },
  senate_progressive: { name: "Senate Progressive Caucus", color: "#7C3AED" },
  senate_dem: { name: "Senate Democratic Caucus", color: "#1D4ED8" },
  senate_gop: { name: "Senate Republican Conference", color: "#DC2626" },
  senate_conservative: { name: "Senate Conservative Fund", color: "#991B1B" },
  senate_bipartisan: { name: "Senate Bipartisan Group", color: "#15803D" },
};

interface Props {
  votes: Vote[];
}

export default function PositionMatrix({ votes }: Props) {
  const yea = votes
    .filter((v) => v.choice === "yea")
    .sort((a, b) => b.weighted_seats - a.weighted_seats);
  const nay = votes
    .filter((v) => v.choice === "nay")
    .sort((a, b) => b.weighted_seats - a.weighted_seats);
  const present = votes
    .filter((v) => v.choice === "present")
    .sort((a, b) => b.weighted_seats - a.weighted_seats);

  const yeaTotal = yea.reduce((s, v) => s + v.weighted_seats, 0);
  const nayTotal = nay.reduce((s, v) => s + v.weighted_seats, 0);

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
      <h2 className="text-lg font-bold text-gray-900 mb-4">Positions at a Glance</h2>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
        {/* YEA column */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-base">✅</span>
            <span className="font-bold text-green-700 text-base">
              YEA — {yeaTotal} seats
            </span>
          </div>
          <div className="border-t border-green-200 pt-2 space-y-1">
            {yea.length === 0 && (
              <p className="text-xs text-gray-400">None</p>
            )}
            {yea.map((v) => {
              const meta = CAUCUS_META[v.caucus_id] ?? {
                name: v.caucus_id,
                color: "#6B7280",
              };
              const truncated =
                v.rationale && v.rationale.length > 80
                  ? v.rationale.slice(0, 80) + "…"
                  : v.rationale;
              return (
                <div key={v.id} className="flex items-start gap-2 py-0.5">
                  <div
                    className="mt-1 w-2.5 h-2.5 rounded-full shrink-0"
                    style={{ backgroundColor: meta.color }}
                  />
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-gray-800">
                      {meta.name}{" "}
                      <span className="text-gray-400 font-normal text-xs">
                        {v.weighted_seats} seats
                      </span>
                    </div>
                    {truncated && (
                      <div className="text-xs text-gray-500 italic leading-snug mt-0.5">
                        {truncated}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* NAY column */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-base">❌</span>
            <span className="font-bold text-red-700 text-base">
              NAY — {nayTotal} seats
            </span>
          </div>
          <div className="border-t border-red-200 pt-2 space-y-1">
            {nay.length === 0 && (
              <p className="text-xs text-gray-400">None</p>
            )}
            {nay.map((v) => {
              const meta = CAUCUS_META[v.caucus_id] ?? {
                name: v.caucus_id,
                color: "#6B7280",
              };
              const truncated =
                v.rationale && v.rationale.length > 80
                  ? v.rationale.slice(0, 80) + "…"
                  : v.rationale;
              return (
                <div key={v.id} className="flex items-start gap-2 py-0.5">
                  <div
                    className="mt-1 w-2.5 h-2.5 rounded-full shrink-0"
                    style={{ backgroundColor: meta.color }}
                  />
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-gray-800">
                      {meta.name}{" "}
                      <span className="text-gray-400 font-normal text-xs">
                        {v.weighted_seats} seats
                      </span>
                    </div>
                    {truncated && (
                      <div className="text-xs text-gray-500 italic leading-snug mt-0.5">
                        {truncated}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* PRESENT row */}
      {present.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-100">
          <div className="flex items-center gap-2 mb-2">
            <span>⚪</span>
            <span className="font-semibold text-gray-600 text-sm">PRESENT</span>
          </div>
          <div className="flex flex-wrap gap-4">
            {present.map((v) => {
              const meta = CAUCUS_META[v.caucus_id] ?? {
                name: v.caucus_id,
                color: "#6B7280",
              };
              return (
                <div key={v.id} className="flex items-center gap-1.5">
                  <div
                    className="w-2.5 h-2.5 rounded-full shrink-0"
                    style={{ backgroundColor: meta.color }}
                  />
                  <span className="text-sm text-gray-700">{meta.name}</span>
                  <span className="text-xs text-gray-400">
                    {v.weighted_seats} seats
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
