import { fetchDebates, fetchBill, type Debate, type Bill } from "@/lib/api";
import DebateCard from "@/components/DebateCard";

export const revalidate = 60;

async function getDebatesWithBills(): Promise<Array<{ debate: Debate; bill: Bill | null }>> {
  try {
    const paged = await fetchDebates(1);
    const items = await Promise.all(
      paged.items.map(async (debate) => {
        let bill: Bill | null = null;
        try {
          bill = await fetchBill(debate.bill_id);
        } catch {
          // bill fetch failed — show debate anyway
        }
        return { debate, bill };
      })
    );
    return items;
  } catch {
    return [];
  }
}

export default async function HomePage() {
  const debates = await getDebatesWithBills();

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Recent Debates</h1>
        <p className="mt-1 text-gray-500 text-sm">
          AI caucus agents debate active US Congress bills. Results are simulated.
        </p>
      </div>

      {debates.length === 0 ? (
        <div className="text-center py-24 text-gray-400">
          <div className="text-5xl mb-4">🏛️</div>
          <p className="text-lg font-medium">No debates yet</p>
          <p className="text-sm mt-1">
            Trigger a bill poll via{" "}
            <code className="bg-gray-100 px-1 rounded">POST /admin/trigger-poll</code> to start.
          </p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-1 md:grid-cols-2">
          {debates.map(({ debate, bill }) => (
            <DebateCard
              key={debate.id}
              debate={debate}
              billTitle={bill?.title}
            />
          ))}
        </div>
      )}
    </div>
  );
}
