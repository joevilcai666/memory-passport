"use client";

import * as React from "react";
import { toast } from "sonner";
import { useMemoryStore } from "@/store/memory-store";

/**
 * Triggers the store's backend hydration once on mount, and surfaces a
 * dismissible toast when the backend is unreachable so the operator knows the
 * UI is rendering the seeded demo dataset instead of live data.
 *
 * Mount this exactly once near the root layout. It renders nothing.
 */
export function StoreHydrator() {
  const hydrate = useMemoryStore((s) => s.hydrate);
  const shownRef = React.useRef(false);

  React.useEffect(() => {
    let cancelled = false;
    void hydrate().then(() => {
      if (cancelled || shownRef.current) return;
      shownRef.current = true;
      // Read the post-hydrate state directly from the store to avoid an
      // extra reactive subscription (the banner only needs to fire once).
      const reachable = useMemoryStore.getState().backendReachable;
      if (!reachable) {
        toast.warning("Memory Passport unavailable — showing demo data", {
          description:
            "Start the backend and check the server-only MP_API_KEY, then reload. Memory edits are blocked until live data is available.",
          duration: Infinity,
          closeButton: true,
        });
      }
    });
    return () => {
      cancelled = true;
    };
  }, [hydrate]);

  return null;
}
