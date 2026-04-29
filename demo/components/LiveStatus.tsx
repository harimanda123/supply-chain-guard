"use client";

import { useEffect, useState } from "react";
import { streamResolution } from "@/lib/api";

interface Props {
  eventId: string;
  initialStatus: string;
}

export default function LiveStatus({ eventId, initialStatus }: Props) {
  const [status, setStatus] = useState(initialStatus);

  useEffect(() => {
    if (status === "pending_approval") {
      const unsub = streamResolution(eventId, (payload) => {
        if (typeof payload.status === "string") {
          setStatus(payload.status);
        }
      });
      return unsub;
    }
  }, [eventId, status]);

  const dot =
    status === "pending_approval"
      ? "bg-blue-500 animate-pulse"
      : status === "approved"
      ? "bg-green-500"
      : status === "escalated" || status === "escalated_stale_data"
      ? "bg-red-500"
      : "bg-gray-400";

  return (
    <span className="inline-flex items-center gap-1.5 text-sm font-medium text-gray-700">
      <span className={`inline-block h-2 w-2 rounded-full ${dot}`} />
      {status.replace(/_/g, " ")}
    </span>
  );
}
