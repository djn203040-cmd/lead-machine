"use client";

import { useState, useTransition } from "react";
import { enqueueEnrichment } from "../enrichment-actions";

// Per-row "Berig" action in the "Ikke beriget" view — queues a single lead.
// Stops row-link navigation so the click doesn't open the lead detail.
export default function EnrichButton({ leadId, status }: { leadId: string; status: string }) {
  const [pending, startTransition] = useTransition();
  const [done, setDone] = useState(false);

  if (status === "queued" || status === "enriching" || done) {
    return <span className="text-xs text-muted">I kø</span>;
  }

  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation();
        e.preventDefault();
        startTransition(async () => {
          const res = await enqueueEnrichment([leadId]);
          if (!res.error) setDone(true);
        });
      }}
      disabled={pending}
      className="btn btn-secondary relative z-10 px-2.5 py-1 text-xs"
    >
      {pending ? "…" : "Berig"}
    </button>
  );
}
