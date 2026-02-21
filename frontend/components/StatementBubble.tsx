import type { Statement } from "@/lib/api";

// Map caucus_id → Tailwind color classes
const CAUCUS_STYLES: Record<string, { bg: string; border: string; label: string; name: string }> = {
  progressive: {
    bg: "bg-purple-100",
    border: "border-purple-400",
    label: "text-purple-800",
    name: "Congressional Progressive Caucus",
  },
  new_dem: {
    bg: "bg-blue-100",
    border: "border-blue-400",
    label: "text-blue-800",
    name: "New Democrat Coalition",
  },
  rsc: {
    bg: "bg-red-100",
    border: "border-red-400",
    label: "text-red-800",
    name: "Republican Study Committee",
  },
  freedom: {
    bg: "bg-rose-100",
    border: "border-rose-500",
    label: "text-rose-900",
    name: "House Freedom Caucus",
  },
  problem_solvers: {
    bg: "bg-green-100",
    border: "border-green-500",
    label: "text-green-800",
    name: "Problem Solvers Caucus",
  },
  cbc: {
    bg: "bg-amber-100",
    border: "border-amber-500",
    label: "text-amber-800",
    name: "Congressional Black Caucus",
  },
  armed_services: {
    bg: "bg-slate-100",
    border: "border-slate-500",
    label: "text-slate-800",
    name: "House Armed Services Committee Bloc",
  },
  senate_progressive: {
    bg: "bg-purple-50",
    border: "border-purple-300",
    label: "text-purple-700",
    name: "Senate Progressive Caucus",
  },
  senate_dem: {
    bg: "bg-blue-50",
    border: "border-blue-300",
    label: "text-blue-700",
    name: "Senate Democratic Caucus",
  },
  senate_gop: {
    bg: "bg-red-50",
    border: "border-red-300",
    label: "text-red-700",
    name: "Senate Republican Conference",
  },
  senate_conservative: {
    bg: "bg-rose-50",
    border: "border-rose-400",
    label: "text-rose-800",
    name: "Senate Conservative Fund",
  },
  senate_bipartisan: {
    bg: "bg-green-50",
    border: "border-green-400",
    label: "text-green-700",
    name: "Senate Bipartisan Group",
  },
};

const TURN_LABELS: Record<string, string> = {
  opening: "Opening Statement",
  debate: "Debate",
  closing: "Closing & Vote",
};

interface Props {
  statement: Statement;
}

export default function StatementBubble({ statement }: Props) {
  const style = CAUCUS_STYLES[statement.caucus_id] ?? {
    bg: "bg-gray-100",
    border: "border-gray-300",
    label: "text-gray-700",
    name: statement.caucus_id,
  };

  const turnLabel = TURN_LABELS[statement.turn_type] ?? statement.turn_type;

  return (
    <div className={`rounded-lg border-l-4 p-4 ${style.bg} ${style.border}`}>
      <div className="flex items-center gap-2 mb-2">
        <span className={`font-semibold text-sm ${style.label}`}>{style.name}</span>
        <span className="text-xs text-gray-400 font-medium uppercase tracking-wide">
          · {turnLabel}
        </span>
      </div>
      <p className="text-sm text-gray-800 leading-relaxed whitespace-pre-wrap">{statement.content}</p>
    </div>
  );
}
