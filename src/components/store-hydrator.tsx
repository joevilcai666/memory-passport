"use client";

import * as React from "react";
import { toast } from "sonner";

import { useMemoryStore } from "@/store/memory-store";

/** Hydrate once and disclose when the UI is showing read-only demo data. */
export function StoreHydrator() {
  const hydrate = useMemoryStore((state) => state.hydrate);
  const shownRef = React.useRef(false);

  React.useEffect(() => {
    let cancelled = false;
    void hydrate().then(() => {
      if (cancelled || shownRef.current) return;
      shownRef.current = true;
      // Read the post-hydrate state directly from the store to avoid an
      // extra reactive subscription (the banner only needs to fire once).
      if (useMemoryStore.getState().dataMode === "offline-demo") {
        toast.warning("Memory Passport unavailable — showing read-only demo data", {
          description:
            "Run `make demo`, check server-only MP_API_URL/MP_API_KEY, then reload. Demo data is never mutated.",
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
