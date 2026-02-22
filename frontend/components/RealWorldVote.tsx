"use client";

import { useState } from "react";
import type { Bill } from "@/lib/api";

interface Props {
  bill: Bill;
  simulationResult: string | null;
}

function normalizeResult(result: string): "passed" | "failed" {
  if (result === "passed" || result === "voice_vote_passed") return "passed";
  return "failed";
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
}

export default function RealWorldVote({ bill, simulationResult }: Props) {
  const [sourceOpen, setSourceOpen] = useState(false);

  const { real_vote_result, real_vote_yea, real_vote_nay, real_vote_date, real_vote_description } = bill;

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-400">
        Real-World Congressional Vote
      </h3>

      {!real_vote_result ? (
        <p className="text-sm text-gray-500">No floor vote recorded yet.</p>
      ) : (
        <>
          {/* Result badge */}
          <div className="flex items-center gap-3 flex-wrap">
            {normalizeResult(real_vote_result) === "passed" ? (
              <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold bg-green-100 text-green-800 border border-green-200">
                PASSED
              </span>
            ) : (
              <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold bg-red-100 text-red-800 border border-red-200">
                FAILED
              </span>
            )}
            {real_vote_result.startsWith("voice_vote") && (
              <span className="text-xs text-gray-500 italic">voice vote</span>
            )}
          </div>

          {/* Roll-call counts */}
          {real_vote_yea != null && real_vote_nay != null && (
            <div className="flex gap-4 text-sm">
              <span className="text-green-700 font-medium">Yea: {real_vote_yea}</span>
              <span className="text-red-700 font-medium">Nay: {real_vote_nay}</span>
            </div>
          )}

          {/* Vote date */}
          {real_vote_date && (
            <p className="text-xs text-gray-500">{formatDate(real_vote_date)}</p>
          )}

          {/* Collapsible raw source */}
          {real_vote_description && (
            <div>
              <button
                onClick={() => setSourceOpen((o) => !o)}
                className="text-xs text-blue-600 hover:underline"
              >
                {sourceOpen ? "Hide" : "Show"} source text
              </button>
              {sourceOpen && (
                <p className="mt-2 text-xs text-gray-600 leading-relaxed border-l-2 border-gray-200 pl-3">
                  {real_vote_description}
                </p>
              )}
            </div>
          )}

          {/* Comparison verdict */}
          {simulationResult && (
            <div className="pt-2 border-t border-gray-100">
              {normalizeResult(real_vote_result) === normalizeResult(simulationResult) ? (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold bg-green-50 text-green-700 border border-green-200">
                  AI MATCHED
                </span>
              ) : (
                <div className="space-y-1">
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold bg-orange-50 text-orange-700 border border-orange-200">
                    AI DIVERGED
                  </span>
                  <p className="text-xs text-gray-500">
                    Congress voted {normalizeResult(real_vote_result).toUpperCase()}, simulation said{" "}
                    {normalizeResult(simulationResult).toUpperCase()}.
                  </p>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
