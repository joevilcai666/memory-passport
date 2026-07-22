"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowRight,
  ArrowLeftRight,
  Check,
  Lock,
  AlertCircle,
  ShieldCheck,
  Cpu,
  ChevronDown,
  ChevronUp,
  Loader2,
} from "lucide-react";
import { AppShell } from "@/components/shell/AppShell";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { useMemoryStore } from "@/store/memory-store";
import { cn } from "@/lib/utils";
import type { MemoryRecord } from "@/lib/types";
import { StampMark } from "@/components/brand/StampMark";
import { toast } from "sonner";

export default function MigrationPreviewPage() {
  const router = useRouter();
  const { memories, migration, selectMigrationMemory, setOldDeviceAccess, executeMigration } =
    useMemoryStore();
  const dataMode = useMemoryStore((state) => state.dataMode);
  const [moving, setMoving] = React.useState(false);

  // Already migrated → redirect to complete
  React.useEffect(() => {
    if (migration.status === "completed" || migration.status === "completed_with_warnings") {
      router.replace("/app/migrate/complete");
    }
  }, [migration.status, router]);

  // Bucket the memories
  const { recommended, needsReview, notMoved } = React.useMemo(() => {
    const rel = memories.filter(
      (m) =>
        m.status !== "deleted" &&
        m.status !== "archived" &&
        m.relationship_id === migration.source_relationship_id,
    );
    return {
      recommended: rel.filter((m) => m.portability.layer === "portable" && m.confidence >= 0.7),
      needsReview: rel.filter((m) => m.portability.layer === "portable" && m.confidence < 0.7),
      notMoved: rel.filter((m) => m.portability.layer === "device_local"),
    };
  }, [memories, migration.source_relationship_id]);

  const selectedCount = migration.selected_memory_ids.length;
  const portableMemories = [...recommended, ...needsReview];
  const skippedCount =
    notMoved.length +
    portableMemories.filter((memory) => !migration.selected_memory_ids.includes(memory.id)).length;

  const allRecommendedSelected = recommended.every((m) =>
    migration.selected_memory_ids.includes(m.id),
  );

  const toggleAllRecommended = () => {
    recommended.forEach((m) => {
      const isSelected = migration.selected_memory_ids.includes(m.id);
      if (allRecommendedSelected && isSelected) selectMigrationMemory(m.id, false);
      else if (!allRecommendedSelected && !isSelected) selectMigrationMemory(m.id, true);
    });
  };

  const handleMove = async () => {
    setMoving(true);
    try {
      const completed = await executeMigration();
      const failedCount = completed.failed_memory_ids.length;
      toast.success(failedCount > 0 ? "Migration completed with warnings" : "Migration completed", {
        description:
          failedCount > 0
            ? `${failedCount} ${failedCount === 1 ? "memory" : "memories"} could not be moved.`
            : `${completed.selected_memory_ids.length} memories processed.`,
      });
      router.push("/app/migrate/complete");
    } catch (error) {
      toast.error("Migration failed", {
        description: error instanceof Error ? error.message : "Please try again.",
      });
    } finally {
      setMoving(false);
    }
  };

  return (
    <AppShell
      headerCenter={
        <div className="flex items-center gap-2">
          <ArrowLeftRight className="size-3.5 text-primary" />
          <span>Move memories</span>
        </div>
      }
      backHref="/app/devices"
    >
      <div className="space-y-5">
        {/* Header / hero */}
        <div className="text-center">
          <div className="mx-auto mb-3 flex items-center justify-center gap-3">
            <DevicePill gen="v1" />
            <motion.div
              animate={{ x: [0, 4, 0] }}
              transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
            >
              <ArrowRight className="size-4 text-primary" />
            </motion.div>
            <DevicePill gen="v2" highlight />
          </div>
          <h1 className="text-xl font-semibold tracking-tight">
            Move memories to Luna Robot v2
          </h1>
          <p className="mx-auto mt-1.5 max-w-xs text-sm text-muted-foreground">
            We found{" "}
            <span className="tabular font-medium text-foreground">
              {recommended.length + needsReview.length + notMoved.length}
            </span>{" "}
            memories that can be moved. Review before continuing.
          </p>
        </div>

        {/* Bucket: Recommended */}
        <Bucket
          title="Recommended"
          subtitle="Portable · travel with you"
          icon={Check}
          iconColor="text-emerald-600"
          accent="emerald"
          count={recommended.length}
          action={
            <button
              onClick={toggleAllRecommended}
              className="text-xs font-medium text-primary hover:underline"
            >
              {allRecommendedSelected ? "Deselect all" : "Select all"}
            </button>
          }
        >
          {recommended.map((m) => (
            <MigrationRow
              key={m.id}
              memory={m}
              checked={migration.selected_memory_ids.includes(m.id)}
              onToggle={(v) => selectMigrationMemory(m.id, v)}
            />
          ))}
        </Bucket>

        {/* Bucket: Needs review */}
        {needsReview.length > 0 && (
          <Bucket
            title="Needs review"
            subtitle="Lower confidence · confirm each"
            icon={AlertCircle}
            iconColor="text-amber-500"
            accent="amber"
            count={needsReview.length}
          >
            {needsReview.map((m) => (
              <MigrationRow
                key={m.id}
                memory={m}
                checked={migration.selected_memory_ids.includes(m.id)}
                onToggle={(v) => selectMigrationMemory(m.id, v)}
                note="Unsure if this should travel. Review the source."
              />
            ))}
          </Bucket>
        )}

        {/* Bucket: Not moved */}
        {notMoved.length > 0 && (
          <Bucket
            title="Not moved"
            subtitle="Device-local · can't travel"
            icon={Lock}
            iconColor="text-muted-foreground"
            accent="muted"
            count={notMoved.length}
            defaultOpen={false}
          >
            {notMoved.map((m) => (
              <div
                key={m.id}
                className="flex items-center gap-3 rounded-lg border bg-muted/30 px-3 py-2.5"
              >
                <Lock className="size-3.5 shrink-0 text-muted-foreground/60" />
                <p className="flex-1 truncate text-sm text-muted-foreground">{m.content}</p>
              </div>
            ))}
            <p className="mt-2 px-1 text-xs text-muted-foreground/80">
              These are tied to v1&apos;s sensors or device-specific state. They stay on v1.
            </p>
          </Bucket>
        )}

        {/* After migration */}
        <div className="rounded-2xl border bg-card p-5">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            After migration
          </p>
          <RadioGroup
            value={migration.old_device_access}
            onValueChange={(v) => setOldDeviceAccess(v as "keep" | "remove")}
            className="mt-3 space-y-2.5"
          >
            <label
              htmlFor="keep"
              className={cn(
                "flex cursor-pointer items-start gap-3 rounded-xl border p-3 transition-colors",
                migration.old_device_access === "keep" && "border-primary bg-primary/5",
              )}
            >
              <RadioGroupItem value="keep" id="keep" className="mt-0.5" />
              <div>
                <p className="text-sm font-medium">Keep v1 access</p>
                <p className="text-xs text-muted-foreground">
                  Both devices can use your memories. v1 stays bound.
                </p>
              </div>
            </label>
            <label
              htmlFor="remove"
              className={cn(
                "flex cursor-pointer items-start gap-3 rounded-xl border p-3 transition-colors",
                migration.old_device_access === "remove" && "border-primary bg-primary/5",
              )}
            >
              <RadioGroupItem value="remove" id="remove" className="mt-0.5" />
              <div>
                <p className="text-sm font-medium">Remove v1 access after v2 is ready</p>
                <p className="text-xs text-muted-foreground">
                  v1 is unbound. Cleaner — recommended when upgrading.
                </p>
              </div>
            </label>
          </RadioGroup>
        </div>

        {/* Sticky CTA */}
        <div className="sticky bottom-0 -mx-5 border-t bg-background/90 px-5 py-4 backdrop-blur-md">
          <Button
            size="lg"
            className="w-full"
            disabled={selectedCount === 0 || moving || dataMode !== "live"}
            onClick={handleMove}
          >
            {moving ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <StampMark className="size-4 text-primary-foreground" />
            )}
            {moving
              ? "Moving memories..."
              : `Move ${selectedCount} ${selectedCount === 1 ? "memory" : "memories"}`}
            {!moving ? <ArrowRight className="size-4" /> : null}
          </Button>
          <p className="mt-2 flex items-center justify-center gap-1.5 text-center text-[11px] text-muted-foreground/70">
            <ShieldCheck className="size-3" />
            Skipping {skippedCount} · recorded in your audit log
          </p>
        </div>
      </div>
    </AppShell>
  );
}

function DevicePill({ gen, highlight }: { gen: string; highlight?: boolean }) {
  return (
    <div
      className={cn(
        "flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium",
        highlight ? "border-primary bg-primary/10 text-primary" : "bg-card text-foreground",
      )}
    >
      <Cpu className="size-3.5" strokeWidth={1.5} />
      Luna {gen}
    </div>
  );
}

function Bucket({
  title,
  subtitle,
  icon: Icon,
  iconColor,
  accent,
  count,
  action,
  children,
  defaultOpen = true,
}: {
  title: string;
  subtitle: string;
  icon: typeof Check;
  iconColor: string;
  accent: "emerald" | "amber" | "muted";
  count: number;
  action?: React.ReactNode;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = React.useState(defaultOpen);
  const accentBg = {
    emerald: "bg-emerald-500/10",
    amber: "bg-amber-500/10",
    muted: "bg-muted",
  }[accent];

  return (
    <div className="overflow-hidden rounded-2xl border bg-card">
      <div className="flex items-center">
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
          className="flex min-w-0 flex-1 cursor-pointer items-center gap-3 p-4 text-left transition-colors hover:bg-accent/40"
        >
        <div className={cn("flex size-8 items-center justify-center rounded-lg", accentBg)}>
          <Icon className={cn("size-4", iconColor)} strokeWidth={1.5} />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium">{title}</p>
          <p className="text-xs text-muted-foreground">{subtitle}</p>
        </div>
        <span className="tabular text-xs font-medium text-muted-foreground">{count}</span>
        {open ? <ChevronUp className="size-4 text-muted-foreground" /> : <ChevronDown className="size-4 text-muted-foreground" />}
        </button>
        {action ? <div className="shrink-0 pr-4">{action}</div> : null}
      </div>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="space-y-2 px-4 pb-4">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function MigrationRow({
  memory,
  checked,
  onToggle,
  note,
}: {
  memory: MemoryRecord;
  checked: boolean;
  onToggle: (v: boolean) => void;
  note?: string;
}) {
  return (
    <label
      className={cn(
        "flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition-colors",
        checked ? "border-primary bg-primary/5" : "hover:border-foreground/20",
      )}
    >
      <Checkbox checked={checked} onCheckedChange={(v) => onToggle(Boolean(v))} className="mt-0.5" />
      <div className="min-w-0 flex-1">
        <p className="text-sm leading-snug">{memory.content}</p>
        <div className="mt-1 flex items-center gap-2">
          <Badge variant="outline" className="text-[10px] capitalize">{memory.type}</Badge>
          {note && <span className="text-[11px] text-amber-600">{note}</span>}
        </div>
      </div>
    </label>
  );
}
