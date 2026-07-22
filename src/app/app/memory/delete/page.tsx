"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, Trash2, Loader2 } from "lucide-react";
import { AppShell } from "@/components/shell/AppShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useMemoryStore } from "@/store/memory-store";
import { toast } from "sonner";

export default function DeleteAllPage() {
  const router = useRouter();
  const deleteAllMemories = useMemoryStore((s) => s.deleteAllMemories);
  const dataMode = useMemoryStore((s) => s.dataMode);
  const [confirmText, setConfirmText] = React.useState("");
  const [deleting, setDeleting] = React.useState(false);
  const canDelete = confirmText === "DELETE";

  const handleDelete = async () => {
    setDeleting(true);
    try {
      const result = await deleteAllMemories();
      toast.success("All memories deleted", {
        description: `${result.tombstoned_memories} memories were tombstoned. Luna will start fresh.`,
      });
      router.push("/app/memory");
    } catch (error) {
      toast.error("Could not delete memories", {
        description: error instanceof Error ? error.message : "Please try again.",
      });
    } finally {
      setDeleting(false);
    }
  };

  return (
    <AppShell title="Delete memory" backHref="/app/memory">
      <div className="space-y-6">
        {/* Warning header */}
        <div className="flex items-start gap-3 rounded-2xl border border-rose-500/30 bg-rose-500/5 p-5">
          <AlertTriangle className="mt-0.5 size-6 shrink-0 text-rose-600" strokeWidth={1.5} />
          <div>
            <h1 className="text-lg font-semibold tracking-tight text-rose-700 dark:text-rose-400">
              Delete all memories?
            </h1>
            <p className="mt-1 text-sm leading-relaxed text-foreground/80">
              This will delete Luna&apos;s long-term memories about you from this app and connected devices.
              Deleted memories will no longer be used in future conversations.
            </p>
          </div>
        </div>

        {/* Fine print */}
        <div className="space-y-2.5 rounded-2xl border bg-card p-5 text-sm text-muted-foreground">
          <p>
            This does <span className="font-medium text-foreground">not</span> delete your account or chat
            history stored by Luna, unless that app says otherwise.
          </p>
          <p>
            Deletion is recorded as a tombstone in the audit log — provable and permanent.
          </p>
          <p>
            Your <span className="font-mono text-xs">passport_id</span> is retained; you can start fresh anytime.
          </p>
        </div>

        {/* Type to confirm */}
        <div className="space-y-2">
          <label htmlFor="delete-confirmation" className="text-sm font-medium">
            Type <span className="font-mono text-rose-600">DELETE</span> to confirm
          </label>
          <Input
            id="delete-confirmation"
            value={confirmText}
            onChange={(e) => setConfirmText(e.target.value)}
            placeholder="DELETE"
            className="font-mono uppercase tracking-widest"
            autoComplete="off"
          />
        </div>

        {/* Actions */}
        <div className="flex gap-2.5">
          <Button variant="outline" size="lg" className="flex-1" onClick={() => router.push("/app/memory")} disabled={deleting}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            size="lg"
            className="flex-1"
            disabled={!canDelete || deleting || dataMode !== "live"}
            onClick={handleDelete}
          >
            {deleting ? <Loader2 className="size-4 animate-spin" /> : <Trash2 className="size-4" />}
            {deleting ? "Deleting..." : "Delete forever"}
          </Button>
        </div>
      </div>
    </AppShell>
  );
}
