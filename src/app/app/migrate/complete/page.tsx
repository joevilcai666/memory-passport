"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Check, ArrowRight, Sparkles, Quote } from "lucide-react";
import { AppShell } from "@/components/shell/AppShell";
import { Button } from "@/components/ui/button";
import { StampMark } from "@/components/brand/StampMark";
import { useMemoryStore } from "@/store/memory-store";

export default function MigrationCompletePage() {
  const router = useRouter();
  const { migration, memories } = useMemoryStore();

  // If not migrated, send back to preview
  React.useEffect(() => {
    if (migration.status !== "completed" && migration.status !== "completed_with_warnings") {
      router.replace("/app/migrate");
    }
  }, [migration.status, router]);

  const failedIds = new Set(migration.failed_memory_ids);
  const movedMemoryIds = migration.selected_memory_ids.filter((id) => !failedIds.has(id));
  const movedCount = movedMemoryIds.length;
  const skippedCount = migration.skipped_memory_ids.length;
  const failedCount = migration.failed_memory_ids.length;
  const v1Access = migration.old_device_access;
  const firstMovedMemory = memories.find((memory) => movedMemoryIds.includes(memory.id));

  return (
    <AppShell showWatermark backHref="/app/devices">
      <div className="flex flex-col items-center py-6 text-center">
        {/* The signature stamp animation */}
        <div className="relative mb-6">
          <motion.div
            initial={{ scale: 0, rotate: -25, opacity: 0 }}
            animate={{ scale: 1, rotate: -8, opacity: 1 }}
            transition={{ type: "spring", stiffness: 220, damping: 16, delay: 0.1 }}
            className="relative"
          >
            <div className="flex size-20 items-center justify-center rounded-full border-2 border-primary/30 bg-primary/5">
              <StampMark className="size-10 text-primary" />
            </div>
            {/* ink ripple */}
            <motion.div
              initial={{ scale: 0.8, opacity: 0.5 }}
              animate={{ scale: 1.8, opacity: 0 }}
              transition={{ duration: 1.2, repeat: 2, ease: "easeOut", delay: 0.3 }}
              className="absolute inset-0 rounded-full border-2 border-primary"
            />
          </motion.div>
          {/* check badge */}
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: "spring", stiffness: 300, damping: 14, delay: 0.6 }}
            className="absolute -bottom-1 -right-1 flex size-7 items-center justify-center rounded-full bg-emerald-500 text-white shadow-md"
          >
            <Check className="size-4" strokeWidth={3} />
          </motion.div>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
        >
          <BadgeRow icon={Sparkles} text="Memories moved" />
          <h1 className="mt-3 text-2xl font-semibold tracking-tight">
            Luna Robot v2 remembers you.
          </h1>
          <p className="mt-2 max-w-xs text-sm text-muted-foreground">
            Your approved memories are now on v2. The relationship continues.
          </p>
        </motion.div>

        {/* v2's first message — the emotional payoff */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.9 }}
          className="mt-6 w-full"
        >
          <div className="relative rounded-2xl border bg-card p-4 text-left">
            <div className="mb-2 flex items-center gap-2">
              <div className="flex size-7 items-center justify-center rounded-full bg-primary/10 text-sm">🌙</div>
              <span className="text-xs font-medium">Luna v2</span>
              <span className="text-[10px] text-muted-foreground">inheriting memory</span>
            </div>
            <div className="flex gap-2">
              <Quote className="size-3 shrink-0 text-primary/40" />
              <p className="text-sm leading-relaxed text-foreground">
                {firstMovedMemory
                  ? `I carried this memory with me: “${firstMovedMemory.content}”`
                  : "Your approved memories have been transferred to this device."}
                <br />
                <span className="text-muted-foreground">Same me. New body. Welcome home.</span>
              </p>
            </div>
          </div>
        </motion.div>

        {/* Stats */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.1 }}
          className="mt-5 grid w-full grid-cols-2 gap-2"
        >
          <Stat label="Moved" value={movedCount} />
          <Stat label="Skipped" value={skippedCount} />
          <Stat label="Failed" value={failedCount} />
          <Stat label="v1 access" value={v1Access === "remove" ? "Removed" : "Kept"} small />
        </motion.div>

        {/* Actions */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.3 }}
          className="mt-6 flex w-full flex-col gap-2.5"
        >
          <Button size="lg" className="w-full" asChild>
            <Link href="/app/memory">
              View memories
              <ArrowRight className="size-4" />
            </Link>
          </Button>
          <Button size="lg" variant="outline" className="w-full" asChild>
            <Link href="/console/devices">See it in console</Link>
          </Button>
        </motion.div>

        <p className="mt-5 text-center text-[11px] text-muted-foreground/70">
          This migration is recorded in your audit log. Cross-device, cross-model — by design.
        </p>
      </div>
    </AppShell>
  );
}

function BadgeRow({ icon: Icon, text }: { icon: typeof Sparkles; text: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/15 px-3 py-1 text-xs font-medium text-emerald-700 dark:text-emerald-400">
      <Icon className="size-3" />
      {text}
    </span>
  );
}

function Stat({ label, value, small }: { label: string; value: number | string; small?: boolean }) {
  return (
    <div className="rounded-xl border bg-card p-3">
      <p className={small ? "tabular text-sm font-semibold" : "tabular text-lg font-semibold"}>{value}</p>
      <p className="mt-0.5 text-[10px] uppercase tracking-wider text-muted-foreground">{label}</p>
    </div>
  );
}
