import Link from "next/link";
import { fetchPending, ResolutionPlan } from "@/lib/api";
import clsx from "clsx";

const STATUS_COLOR: Record<string, string> = {
  pending_approval: "bg-blue-100 text-blue-800",
  escalated: "bg-red-100 text-red-800",
  approved: "bg-green-100 text-green-800",
  rejected: "bg-gray-100 text-gray-600",
};

export default async function Dashboard() {
  let plans: ResolutionPlan[] = [];
  let error = "";
  try {
    plans = await fetchPending();
  } catch (e: unknown) {
    error = e instanceof Error ? e.message : "API unavailable";
  }

  return (
    <main className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Supply Chain Guard</h1>
            <p className="text-sm text-gray-500 mt-1">Pending resolution approvals</p>
          </div>
          <span className="text-xs text-gray-400">{plans.length} awaiting review</span>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-lg bg-red-50 text-red-700 text-sm">
            Could not connect to API: {error}. Make sure the server is running on
            port 8000.
          </div>
        )}

        {!error && plans.length === 0 && (
          <div className="text-center py-20 text-gray-400">
            No pending approvals. Post a disruption event to get started.
          </div>
        )}

        <div className="grid gap-4">
          {plans.map((plan) => (
            <Link
              key={plan.event_id}
              href={`/resolution/${plan.event_id}`}
              className="block bg-white rounded-xl shadow-sm border border-gray-100 p-6 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs text-gray-400 font-mono mb-1">
                    {plan.event_id}
                  </p>
                  <p className="font-semibold text-gray-800">
                    {plan.recommended_carrier || "Carrier TBD"}
                  </p>
                  <p className="text-sm text-gray-500 mt-0.5">
                    {plan.recommended_mode.toUpperCase()} &middot;{" "}
                    {plan.estimated_eta_days} days
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-lg font-bold text-gray-900">
                    ${plan.estimated_cost.toLocaleString()}
                  </p>
                  <span
                    className={clsx(
                      "mt-1 inline-block text-xs font-medium px-2 py-0.5 rounded-full",
                      STATUS_COLOR[plan.status] ?? "bg-gray-100 text-gray-600"
                    )}
                  >
                    {plan.status.replace(/_/g, " ")}
                  </span>
                </div>
              </div>
              <p className="mt-3 text-xs text-gray-500 truncate">
                {plan.cost_vs_penalty}
              </p>
            </Link>
          ))}
        </div>
      </div>
    </main>
  );
}
