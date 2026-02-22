import type { Bill } from "@/lib/api";

function formatDate(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
}

interface Props {
  bill: Bill;
}

export default function BillSummary({ bill }: Props) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 text-sm">
      <h2 className="font-bold text-base text-gray-900 mb-3 leading-snug">{bill.title}</h2>

      <dl className="space-y-1.5 text-gray-700">
        {bill.bill_type && bill.congress_number && (
          <div className="flex gap-2">
            <dt className="text-gray-400 w-28 shrink-0">Bill</dt>
            <dd className="font-medium uppercase">
              {bill.bill_type}.{bill.congress_number && ` (${bill.congress_number}th Congress)`}
            </dd>
          </div>
        )}
        <div className="flex gap-2">
          <dt className="text-gray-400 w-28 shrink-0">Chamber</dt>
          <dd>{bill.chamber ?? "—"}</dd>
        </div>
        <div className="flex gap-2">
          <dt className="text-gray-400 w-28 shrink-0">Sponsor</dt>
          <dd>{bill.sponsor ?? "—"}</dd>
        </div>
        <div className="flex gap-2">
          <dt className="text-gray-400 w-28 shrink-0">Introduced</dt>
          <dd>{formatDate(bill.introduced_date)}</dd>
        </div>
        <div className="flex gap-2">
          <dt className="text-gray-400 w-28 shrink-0">Last Action</dt>
          <dd>{formatDate(bill.last_action_date)}</dd>
        </div>
        {bill.last_action_text && (
          <div className="flex gap-2">
            <dt className="text-gray-400 w-28 shrink-0">Status</dt>
            <dd className="text-gray-600 leading-snug">{bill.last_action_text}</dd>
          </div>
        )}
      </dl>

      {bill.congress_url && (
        <div className="mt-4">
          <a
            href={bill.congress_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-xs text-blue-600 hover:text-blue-800 hover:underline font-medium"
          >
            View on Congress.gov ↗
          </a>
        </div>
      )}

      {bill.summary && (
        <div className="mt-4 pt-4 border-t border-gray-100">
          <p className="text-xs text-gray-400 uppercase tracking-wide font-semibold mb-1">Summary</p>
          <p
            className="text-gray-600 leading-relaxed text-xs line-clamp-10"
            dangerouslySetInnerHTML={{ __html: bill.summary }}
          />
        </div>
      )}
    </div>
  );
}
