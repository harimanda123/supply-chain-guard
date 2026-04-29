"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { submitApproval } from "@/lib/api";

interface Props {
  eventId: string;
}

export default function ApprovalButtons({ eventId }: Props) {
  const router = useRouter();
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState<"approve" | "reject" | null>(null);
  const [result, setResult] = useState<string | null>(null);

  async function handle(approved: boolean) {
    setLoading(approved ? "approve" : "reject");
    try {
      const res = await submitApproval(eventId, approved, note || undefined);
      setResult(res.message);
      setTimeout(() => router.push("/"), 1500);
    } catch (e: unknown) {
      setResult(e instanceof Error ? e.message : "Error submitting approval");
    } finally {
      setLoading(null);
    }
  }

  if (result) {
    return (
      <p className="text-sm font-medium text-green-700 bg-green-50 rounded-lg p-3">
        {result}
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <textarea
        className="w-full rounded-lg border border-gray-200 p-3 text-sm text-gray-700 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-300 resize-none"
        rows={2}
        placeholder="Optional reviewer note..."
        value={note}
        onChange={(e) => setNote(e.target.value)}
      />
      <div className="flex gap-3">
        <button
          onClick={() => handle(true)}
          disabled={!!loading}
          className="flex-1 rounded-lg bg-green-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-green-700 disabled:opacity-50 transition-colors"
        >
          {loading === "approve" ? "Approving…" : "Approve & Book"}
        </button>
        <button
          onClick={() => handle(false)}
          disabled={!!loading}
          className="flex-1 rounded-lg border border-red-200 bg-red-50 px-4 py-2.5 text-sm font-semibold text-red-700 hover:bg-red-100 disabled:opacity-50 transition-colors"
        >
          {loading === "reject" ? "Rejecting…" : "Reject"}
        </button>
      </div>
    </div>
  );
}
