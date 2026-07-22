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
      if (useMemoryStore.getState().dataMode === "offline-demo") {
        toast.warning("Backend offline — showing read-only demo data", {
          description:
            "Start the backend with `make demo` and reload to enable real writes. Demo data is never mutated.",
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
