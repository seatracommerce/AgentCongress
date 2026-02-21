import Link from "next/link";
import type { Debate } from "@/lib/api";

const RESULT_STYLES = {
  passed: "bg-green-100 text-green-800 border border-green-300",
  failed: "bg-red-100 text-red-800 border border-red-300",
};

function formatDate(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

interface Props {
  debate: Debate;
  billTitle?: string;
}

export default function DebateCard({ debate, billTitle }: Props) {
  const resultLabel = debate.result ?? "pending";
  const resultStyle =
    RESULT_STYLES[resultLabel as keyof typeof RESULT_STYLES] ??
    "bg-gray-100 text-gray-700 border border-gray-200";

  const yea = debate.yea_seats ?? 0;
  const nay = debate.nay_seats ?? 0;
  const total = yea + nay + (debate.present_seats ?? 0);

  return (
    <Link href={`/debates/${debate.id}`} className="block group">
      <div className="bg-white rounded-xl border border-gray-200 p-5 hover:border-blue-400 hover:shadow-md transition-all">
        <div className="flex items-start justify-between gap-3">
          <h2 className="text-base font-semibold text-gray-900 group-hover:text-blue-700 leading-snug line-clamp-2">
            {billTitle ?? `Debate #${debate.id}`}
          </h2>
          {debate.result && (
            <span className={`shrink-0 text-xs font-bold px-2.5 py-1 rounded-full ${resultStyle}`}>
              {debate.result === "passed" ? "✅ PASSED" : "❌ FAILED"}
            </span>
          )}
        </div>

        {total > 0 && (
          <div className="mt-3">
            <div className="flex rounded-full overflow-hidden h-1.5">
              {yea > 0 && (
                <div className="bg-green-500" style={{ width: `${(yea / total) * 100}%` }} />
              )}
              {(debate.present_seats ?? 0) > 0 && (
                <div
                  className="bg-gray-300"
                  style={{ width: `${((debate.present_seats ?? 0) / total) * 100}%` }}
                />
              )}
              {nay > 0 && (
                <div className="bg-red-500" style={{ width: `${(nay / total) * 100}%` }} />
              )}
            </div>
            <p className="mt-1 text-xs text-gray-400">{yea} YEA · {nay} NAY</p>
          </div>
        )}

        <div className="mt-3 flex items-center gap-4 text-xs text-gray-500">
          <span>{formatDate(debate.completed_at ?? debate.created_at)}</span>
          <span
            className={`ml-auto px-2 py-0.5 rounded text-xs font-medium ${
              debate.status === "completed"
                ? "bg-gray-100 text-gray-600"
                : debate.status === "running"
                ? "bg-yellow-100 text-yellow-700"
                : "bg-gray-100 text-gray-400"
            }`}
          >
            {debate.status}
          </span>
        </div>
      </div>
    </Link>
  );
}
