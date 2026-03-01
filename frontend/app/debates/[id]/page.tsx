import { notFound } from "next/navigation";
import { fetchDebate, fetchBill, type Statement } from "@/lib/api";
import StatementBubble from "@/components/StatementBubble";
import VoteBoard from "@/components/VoteBoard";
import BillSummary from "@/components/BillSummary";
import RealWorldVote from "@/components/RealWorldVote";

export const dynamic = "force-dynamic";
export const revalidate = 60;

interface Props {
  params: { id: string };
}

function groupStatements(statements: Statement[]) {
  const groups: { label: string; items: Statement[] }[] = [];
  let currentTurn: string | null = null;
  let currentGroup: Statement[] = [];
  let debateRound = 0;

  const sorted = [...statements].sort((a, b) => a.sequence - b.sequence);

  for (const stmt of sorted) {
    if (stmt.turn_type !== currentTurn) {
      if (currentGroup.length) {
        let label =
          currentTurn === "opening"
            ? "Opening Statements"
            : currentTurn === "closing"
              ? "Closing Statements & Votes"
              : `Debate Round ${debateRound}`;
        groups.push({ label, items: currentGroup });
      }
      currentTurn = stmt.turn_type;
      currentGroup = [stmt];
      if (stmt.turn_type === "debate") debateRound++;
    } else {
      currentGroup.push(stmt);
    }
  }
  if (currentGroup.length) {
    const label =
      currentTurn === "opening"
        ? "Opening Statements"
        : currentTurn === "closing"
          ? "Closing Statements & Votes"
          : `Debate Round ${debateRound}`;
    groups.push({ label, items: currentGroup });
  }

  return groups;
}

export default async function DebatePage({ params }: Props) {
  const id = parseInt(params.id, 10);
  if (isNaN(id)) notFound();

  let debate, bill;
  try {
    debate = await fetchDebate(id);
  } catch {
    notFound();
  }

  try {
    bill = await fetchBill(debate.bill_id);
  } catch {
    bill = null;
  }

  const statements = debate.statements ?? [];
  const votes = debate.votes ?? [];
  const groups = groupStatements(statements);

  return (
    <div className="space-y-8">
      {/* Page title */}
      <div>
        <a href="/" className="text-sm text-blue-600 hover:underline">
          ← All debates
        </a>
        <div className="flex items-center gap-2 mt-2 flex-wrap">
          <h1 className="text-2xl font-bold text-gray-900 leading-snug">
            {bill?.title ?? `Debate #${debate.id}`}
          </h1>
          {debate.chamber && (
            <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full border shrink-0 bg-gray-50 text-gray-600 border-gray-300">
              {debate.chamber === "Senate" ? "🏛️ Senate" : "🏠 House"}
            </span>
          )}
        </div>
        {debate.status === "running" && (
          <span className="inline-block mt-2 text-xs bg-yellow-100 text-yellow-700 border border-yellow-300 px-2 py-1 rounded-full animate-pulse">
            Debate in progress…
          </span>
        )}
      </div>

      {/* 1. Agent Congress vote result — top, wide view */}
      {votes.length > 0 && debate.yea_seats != null && (
        <section className="w-full">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500 mb-4">
            Agent Congress vote result
          </h2>
          <VoteBoard
            votes={votes}
            yea_seats={debate.yea_seats}
            nay_seats={debate.nay_seats ?? 0}
            present_seats={debate.present_seats ?? 0}
            result={debate.result ?? "unknown"}
          />
        </section>
      )}

      {/* 2. Real-world Congress result */}
      {bill && (
        <section className="w-full">
          <RealWorldVote bill={bill} simulationResult={debate.result} />
        </section>
      )}

      {/* 3. Bill information */}
      {bill && (
        <section className="w-full">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500 mb-4">
            Bill information
          </h2>
          <BillSummary bill={bill} />
        </section>
      )}

      {/* 4. Debate summary */}
      {debate.summary && (
        <section className="w-full">
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500 mb-3">
              Debate summary
            </h2>
            <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
              {debate.summary}
            </p>
          </div>
        </section>
      )}

      {/* 5. Full transcript — collapsed at the end */}
      <section className="w-full">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500 mb-4">
          Transcript
        </h2>
        {groups.length === 0 ? (
          <p className="text-gray-400 text-sm">No statements yet.</p>
        ) : (
          <details className="group">
            <summary className="cursor-pointer text-sm font-semibold text-gray-600 hover:text-gray-900 py-2">
              Full transcript ({statements.length} statements)
            </summary>
            <div className="mt-4 space-y-8">
              {groups.map((group) => (
                <details key={group.label} open>
                  <summary className="cursor-pointer text-xs font-bold uppercase tracking-widest text-gray-400 border-b border-gray-100 pb-1">
                    {group.label}
                  </summary>
                  <div className="space-y-3 mt-3">
                    {group.items.map((stmt) => (
                      <StatementBubble key={stmt.id} statement={stmt} />
                    ))}
                  </div>
                </details>
              ))}
            </div>
          </details>
        )}
      </section>
    </div>
  );
}
