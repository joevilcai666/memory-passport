"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Check, X, ShieldCheck, Sparkles, Loader2 } from "lucide-react";
import { AppShell } from "@/components/shell/AppShell";
import { Button } from "@/components/ui/button";
import { useMemoryStore } from "@/store/memory-store";
import { toast } from "sonner";

const mayRemember = [
  "Your preferences",
  "Important things you tell Luna",
  "Boundaries, dislikes, and reminders",
];

const willNotSave = [
  "Sensitive health or financial info",
  "Temporary chats",
  "Anything you delete",
];

export default function ConsentPage() {
  const router = useRouter();
  const setMemoryEnabled = useMemoryStore((s) => s.setMemoryEnabled);
  const [turningOn, setTurningOn] = React.useState(false);

  const handleTurnOn = async () => {
    if (turningOn) return;
    setTurningOn(true);
    try {
      await setMemoryEnabled(true);
      toast.success("Memory is on", { description: "Luna will remember what matters to you." });
      router.push("/app/memory");
    } catch (error) {
      toast.error("Memory could not be enabled", {
        description: error instanceof Error ? error.message : "Unknown error",
      });
    } finally {
      setTurningOn(false);
    }
  };

  return (
    <AppShell title="Memory" backHref="/app/memory" showWatermark>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center gap-3">
          <div className="flex size-12 items-center justify-center rounded-2xl bg-primary/10">
            <Sparkles className="size-6 text-primary" strokeWidth={1.5} />
          </div>
          <div>
            <h1 className="text-xl font-semibold tracking-tight">Luna can remember you</h1>
            <p className="text-sm text-muted-foreground">So future conversations feel more continuous.</p>
          </div>
        </div>

        {/* What Luna may remember */}
        <div className="rounded-2xl border bg-card p-5">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            What Luna may remember
          </p>
          <ul className="mt-3 space-y-2.5">
            {mayRemember.map((item) => (
              <li key={item} className="flex items-start gap-2.5">
                <div className="mt-0.5 flex size-4 shrink-0 items-center justify-center rounded-full bg-emerald-500/15 text-emerald-600">
                  <Check className="size-3" strokeWidth={2.5} />
                </div>
                <span className="text-sm">{item}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* What Luna will not save */}
        <div className="rounded-2xl border bg-card p-5">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            What Luna will not save by default
          </p>
          <ul className="mt-3 space-y-2.5">
            {willNotSave.map((item) => (
              <li key={item} className="flex items-start gap-2.5">
                <div className="mt-0.5 flex size-4 shrink-0 items-center justify-center rounded-full bg-rose-500/15 text-rose-600">
                  <X className="size-3" strokeWidth={2.5} />
                </div>
                <span className="text-sm text-muted-foreground">{item}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Ownership statement */}
        <div className="flex items-start gap-3 rounded-2xl bg-primary/5 p-5">
          <ShieldCheck className="mt-0.5 size-5 shrink-0 text-primary" strokeWidth={1.5} />
          <div>
            <p className="text-sm font-medium text-foreground">
              Your memories belong to you, not Luna.
            </p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              You can view, edit, or delete anytime. They travel with you across devices and models.
            </p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex flex-col gap-2.5">
          <Button size="lg" onClick={handleTurnOn} className="w-full" disabled={turningOn}>
            {turningOn && <Loader2 className="size-4 animate-spin" />}
            {turningOn ? "Turning on..." : "Turn on"}
          </Button>
          <Button size="lg" variant="outline" className="w-full" onClick={() => router.push("/app/memory")}>
            Not now
          </Button>
        </div>

        <p className="text-center text-[11px] text-muted-foreground/70">
          You can change this anytime in Memory settings.{" "}
          <Link href="/app/memory" className="underline underline-offset-2 hover:text-foreground">
            See what Luna remembers
          </Link>
        </p>
      </div>
    </AppShell>
  );
}
