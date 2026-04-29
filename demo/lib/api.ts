const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface AuditEntry {
  agent: string;
  finding: string;
  decision: string;
}

export interface ResolutionPlan {
  event_id: string;
  recommended_carrier: string;
  recommended_mode: string;
  estimated_cost: number;
  estimated_eta_days: number;
  cost_vs_penalty: string;
  audit_trail: AuditEntry[];
  status: string;
  created_at: string;
}

export interface DisruptionEvent {
  event_id: string;
  source_system: string;
  event_type: string;
  shipment_id: string;
  affected_skus: { sku: string; qty: number }[];
  severity: string;
  status: string;
  received_at: string;
}

export async function fetchPending(): Promise<ResolutionPlan[]> {
  const res = await fetch(`${BASE}/api/v1/approvals/pending`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch pending approvals");
  return res.json();
}

export async function fetchResolution(eventId: string): Promise<ResolutionPlan> {
  const res = await fetch(`${BASE}/api/v1/approvals/${eventId}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Resolution not ready");
  return res.json();
}

export async function submitApproval(
  eventId: string,
  approved: boolean,
  reviewerNote?: string
): Promise<{ event_id: string; status: string; message: string }> {
  const res = await fetch(`${BASE}/api/v1/approvals/${eventId}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ event_id: eventId, approved, reviewer_note: reviewerNote }),
  });
  if (!res.ok) throw new Error("Approval submission failed");
  return res.json();
}

export function streamResolution(
  eventId: string,
  onEvent: (payload: Record<string, unknown>) => void
): () => void {
  const source = new EventSource(
    `${BASE}/api/v1/approvals/stream/${eventId}`
  );
  source.onmessage = (e) => {
    try {
      onEvent(JSON.parse(e.data));
    } catch {
      // ignore malformed frames
    }
  };
  return () => source.close();
}
