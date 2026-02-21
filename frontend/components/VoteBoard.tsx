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

const CHOICE_STYLE = {
  yea: "bg-green-100 text-green-800 border border-green-300",
  nay: "bg-red-100 text-red-800 border border-red-300",
  present: "bg-gray-100 text-gray-600 border border-gray-300",
};

// Parliament arc chart helpers
const CX = 100, CY = 100, OUTER_R = 85, INNER_R = 57;

function toRad(deg: number) {
  return (deg * Math.PI) / 180;
}

function svgPt(r: number, deg: number): [number, number] {
  return [
    CX + r * Math.cos(toRad(deg)),
    CY - r * Math.sin(toRad(deg)),
  ];
}

// Draw a ring arc segment from startDeg to endDeg (standard math angles, CCW positive).
// YEA: startDeg > endDeg (going from 180° toward 0°, sweepOuter=1 CW in SVG = through top).
// NAY: startDeg < endDeg (going from 0° toward 180°, sweepOuter=0 CCW in SVG = through top).
function arcSeg(startDeg: number, endDeg: number): string {
  if (Math.abs(endDeg - startDeg) < 0.1) return "";
  const large = Math.abs(endDeg - startDeg) >= 180 ? 1 : 0;
  const swo = startDeg > endDeg ? 1 : 0;
  const swi = 1 - swo;
  const [ox1, oy1] = svgPt(OUTER_R, startDeg);
  const [ox2, oy2] = svgPt(OUTER_R, endDeg);
  const [ix2, iy2] = svgPt(INNER_R, endDeg);
  const [ix1, iy1] = svgPt(INNER_R, startDeg);
  const f = (n: number) => n.toFixed(2);
  return (
    `M ${f(ox1)} ${f(oy1)} ` +
    `A ${OUTER_R} ${OUTER_R} 0 ${large} ${swo} ${f(ox2)} ${f(oy2)} ` +
    `L ${f(ix2)} ${f(iy2)} ` +
    `A ${INNER_R} ${INNER_R} 0 ${large} ${swi} ${f(ix1)} ${f(iy1)} Z`
  );
}

interface Props {
  votes: Vote[];
  yea_seats: number;
  nay_seats: number;
  present_seats: number;
  result: string;
}

export default function VoteBoard({ votes, yea_seats, nay_seats, present_seats, result }: Props) {
  const total = yea_seats + nay_seats + present_seats;
  const yeaPct = total ? (yea_seats / total) * 100 : 0;
  const nayPct = total ? (nay_seats / total) * 100 : 0;
  const presentPct = total ? (present_seats / total) * 100 : 0;
  const threshold = Math.ceil(total / 2);

  // Parliament arc segments
  const yeaVotes = votes
    .filter((v) => v.choice === "yea")
    .sort((a, b) => b.weighted_seats - a.weighted_seats);
  const nayVotes = votes
    .filter((v) => v.choice === "nay")
    .sort((a, b) => b.weighted_seats - a.weighted_seats);

  let yeaAngle = 180;
  const yeaSegs = yeaVotes.map((v) => {
    const span = total > 0 ? (v.weighted_seats / total) * 180 : 0;
    const start = yeaAngle;
    const end = yeaAngle - span;
    yeaAngle = end;
    return { path: arcSeg(start, end), color: (CAUCUS_META[v.caucus_id] ?? { color: "#6B7280" }).color };
  });

  let nayAngle = 0;
  const naySegs = nayVotes.map((v) => {
    const span = total > 0 ? (v.weighted_seats / total) * 180 : 0;
    const start = nayAngle;
    const end = nayAngle + span;
    nayAngle = end;
    return { path: arcSeg(start, end), color: (CAUCUS_META[v.caucus_id] ?? { color: "#6B7280" }).color };
  });

  // PRESENT gap between yeaAngle (left remainder) and nayAngle (right remainder)
  const presentPath = yeaAngle > nayAngle ? arcSeg(nayAngle, yeaAngle) : "";

  // Threshold tick line
  const thresholdAngle = total > 0 ? 180 - (threshold / total) * 180 : 90;
  const [tx1, ty1] = svgPt(INNER_R - 4, thresholdAngle);
  const [tx2, ty2] = svgPt(OUTER_R + 4, thresholdAngle);
  const [tlx, tly] = svgPt(OUTER_R + 14, thresholdAngle);

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h2 className="text-lg font-bold text-gray-900 mb-4">Vote Results</h2>

      {/* Parliament arc chart */}
      {total > 0 && (
        <svg
          viewBox="0 0 200 118"
          className="w-full max-w-[200px] mx-auto mb-5 block"
          aria-label="Parliament vote chart"
        >
          {/* YEA arc segments (left side) */}
          {yeaSegs.map((seg, i) =>
            seg.path ? (
              <path key={`yea-${i}`} d={seg.path} fill={seg.color} stroke="white" strokeWidth="1" />
            ) : null
          )}

          {/* NAY arc segments (right side) */}
          {naySegs.map((seg, i) =>
            seg.path ? (
              <path key={`nay-${i}`} d={seg.path} fill={seg.color} stroke="white" strokeWidth="1" />
            ) : null
          )}

          {/* PRESENT gap */}
          {presentPath && (
            <path d={presentPath} fill="#D1D5DB" stroke="white" strokeWidth="1" />
          )}

          {/* Threshold tick */}
          <line
            x1={tx1.toFixed(2)} y1={ty1.toFixed(2)}
            x2={tx2.toFixed(2)} y2={ty2.toFixed(2)}
            stroke="#374151" strokeWidth="1.5" strokeLinecap="round"
          />
          <text
            x={tlx.toFixed(2)}
            y={tly.toFixed(2)}
            textAnchor="middle"
            fontSize="5.5"
            fill="#6B7280"
            dominantBaseline="middle"
          >
            pass
          </text>

          {/* Seat count labels */}
          <text x="5" y="113" fontSize="8" fill="#15803D" fontWeight="600">
            {yea_seats} YEA
          </text>
          <text x="195" y="113" textAnchor="end" fontSize="8" fill="#DC2626" fontWeight="600">
            {nay_seats} NAY
          </text>
        </svg>
      )}

      {/* Summary bar */}
      <div className="flex rounded-full overflow-hidden h-6 mb-3">
        {yeaPct > 0 && (
          <div
            className="bg-green-500 flex items-center justify-center text-white text-xs font-bold"
            style={{ width: `${yeaPct}%` }}
          >
            {yeaPct > 8 ? `${yea_seats}` : ""}
          </div>
        )}
        {presentPct > 0 && (
          <div
            className="bg-gray-300 flex items-center justify-center text-gray-600 text-xs"
            style={{ width: `${presentPct}%` }}
          >
            {presentPct > 8 ? `${present_seats}` : ""}
          </div>
        )}
        {nayPct > 0 && (
          <div
            className="bg-red-500 flex items-center justify-center text-white text-xs font-bold"
            style={{ width: `${nayPct}%` }}
          >
            {nayPct > 8 ? `${nay_seats}` : ""}
          </div>
        )}
      </div>

      <div className="flex gap-4 text-sm mb-1">
        <span className="text-green-700 font-semibold">✅ YEA: {yea_seats} seats</span>
        <span className="text-red-700 font-semibold">❌ NAY: {nay_seats} seats</span>
        {present_seats > 0 && (
          <span className="text-gray-500">⚪ PRESENT: {present_seats} seats</span>
        )}
      </div>
      <p className="text-xs text-gray-400 mb-5">
        Threshold to pass: {threshold} seats ({total} total active seats)
      </p>

      {/* Final result */}
      <div
        className={`inline-flex items-center gap-2 px-4 py-2 rounded-full font-bold text-sm mb-6 ${
          result === "passed"
            ? "bg-green-100 text-green-800 border border-green-300"
            : "bg-red-100 text-red-800 border border-red-300"
        }`}
      >
        {result === "passed" ? "✅ PASSED" : "❌ FAILED"}
      </div>

      {/* Per-caucus breakdown */}
      <h3 className="text-sm font-semibold text-gray-700 mb-3 uppercase tracking-wide">
        Caucus Breakdown
      </h3>
      <div className="space-y-3">
        {votes.map((vote) => {
          const meta = CAUCUS_META[vote.caucus_id] ?? {
            name: vote.caucus_id,
            color: "#6B7280",
          };
          const choiceStyle =
            CHOICE_STYLE[vote.choice as keyof typeof CHOICE_STYLE] ?? CHOICE_STYLE.present;

          return (
            <div key={vote.id} className="flex items-start gap-3">
              <div
                className="mt-0.5 w-3 h-3 rounded-full shrink-0"
                style={{ backgroundColor: meta.color }}
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-medium text-sm text-gray-800">{meta.name}</span>
                  <span className="text-xs text-gray-400">{vote.weighted_seats} seats</span>
                  <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${choiceStyle}`}>
                    {vote.choice.toUpperCase()}
                  </span>
                </div>
                {vote.rationale && (
                  <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">{vote.rationale}</p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
