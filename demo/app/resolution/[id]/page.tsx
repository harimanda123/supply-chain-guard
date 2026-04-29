import { fetchResolution } from "@/lib/api";
import { notFound } from "next/navigation";
import Link from "next/link";
import LiveStatus from "@/components/LiveStatus";
import ApprovalButtons from "@/components/ApprovalButtons";

interface Props {
  params: Promise<{ id: string }>;
}

const AGENT_COLORS: Record<string, string> = {
  "Inventory Analyst": "bg-purple-100 text-purple-800",
  "Logistics Strategist": "bg-blue-100 text-blue-800",
  "Financial Controller": "bg-yellow-100 text-yellow-800",
  "Compliance Auditor": "bg-green-100 text-green-800",
};

export default async function ResolutionPage({ params }: Props) {
  const { id } = await params;

  let plan;
  try {
    plan = await fetchResolution(id);
  } catch {
    notFound();
  }

  const isPending = plan.status === "pending_approval";

  return (
    <main className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-3xl mx-auto space-y-6">
        {/* Back */}
        <Link href="/" className="text-sm text-gray-500 hover:text-gray-800">
          ← Back to dashboard
        </Link>

        {/* Header card */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-mono text-gray-400 mb-1">{plan.event_id}</p>
              <h2 className="text-xl font-bold text-gray-900">
                {plan.recommended_carrier || "Resolution Plan"}
              </h2>
              <p className="text-sm text-gray-500 mt-0.5">
                {plan.recommended_mode?.toUpperCase()} &middot;{" "}
                {plan.estimated_eta_days} days transit
              </p>
            </div>
            <LiveStatus eventId={plan.event_id} initialStatus={plan.status} />
          </div>

          <div className="mt-5 grid grid-cols-3 gap-4">
            <div className="rounded-lg bg-gray-50 p-3">
              <p className="text-xs text-gray-400">Estimated cost</p>
              <p className="text-lg font-bold text-gray-900">
                ${plan.estimated_cost.toLocaleString()}
              </p>
            </div>
            <div className="rounded-lg bg-gray-50 p-3">
              <p className="text-xs text-gray-400">Transit time</p>
              <p className="text-lg font-bold text-gray-900">
                {plan.estimated_eta_days}d
              </p>
            </div>
            <div className="rounded-lg bg-gray-50 p-3">
              <p className="text-xs text-gray-400">Created</p>
              <p className="text-sm font-semibold text-gray-900">
                {new Date(plan.created_at).toLocaleDateString()}
              </p>
            </div>
          </div>

          {plan.cost_vs_penalty && (
            <p className="mt-4 text-xs text-gray-500 bg-blue-50 rounded-lg p-3">
              {plan.cost_vs_penalty}
            </p>
          )}
        </div>

        {/* Approval card — only for pending */}
        {isPending && (
          <div className="bg-white rounded-xl shadow-sm border border-blue-100 p-6">
            <h3 className="text-sm font-semibold text-gray-800 mb-3">
              Human Review Required
            </h3>
            <ApprovalButtons eventId={plan.event_id} />
          </div>
        )}

        {/* Audit trail */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h3 className="text-sm font-semibold text-gray-800 mb-4">
            Agent Audit Trail
          </h3>
          {plan.audit_trail.length === 0 ? (
            <p className="text-sm text-gray-400">No audit entries yet.</p>
          ) : (
            <ol className="space-y-4">
              {plan.audit_trail.map((entry, i) => (
                <li key={i} className="flex gap-4">
                  <div className="flex flex-col items-center">
                    <span className="flex h-7 w-7 items-center justify-center rounded-full bg-gray-100 text-xs font-bold text-gray-500">
                      {i + 1}
                    </span>
                    {i < plan.audit_trail.length - 1 && (
                      <div className="mt-1 w-px flex-1 bg-gray-100" />
                    )}
                  </div>
                  <div className="pb-4 flex-1">
                    <span
                      className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                        AGENT_COLORS[entry.agent] ?? "bg-gray-100 text-gray-600"
                      }`}
                    >
                      {entry.agent}
                    </span>
                    <p className="mt-2 text-sm text-gray-700">{entry.finding}</p>
                    <p className="mt-1 text-xs text-gray-400 font-mono">
                      {entry.decision}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </div>
      </div>
    </main>
  );
}
