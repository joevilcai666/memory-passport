"use client";

import Link from "next/link";
import {
  Users,
  Zap,
  ThumbsUp,
  AlertTriangle,
  ArrowLeftRight,
  Shuffle,
  ArrowRight,
  AlertCircle,
  Info,
  CheckCircle2,
  Rocket,
  Circle,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { KpiTile } from "@/components/console/KpiTile";
import { ActivityChart } from "@/components/console/ActivityChart";
import { useMemoryStore } from "@/store/memory-store";
import { formatRelativeDay } from "@/lib/utils";
import type { AlertSeverity } from "@/lib/types";

const severityConfig: Record<AlertSeverity, { icon: typeof AlertCircle; color: string }> = {
  warning: { icon: AlertTriangle, color: "text-amber-500" },
  error: { icon: AlertCircle, color: "text-rose-500" },
  info: { icon: Info, color: "text-ink-500" },
};

export default function OverviewPage() {
  const { kpis, alerts, app, tenant, memories, quickstart } = useMemoryStore();

  return (
    <div className="space-y-6">
      {/* Greeting */}
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-medium tracking-tight">Overview</h1>
        <p className="text-sm text-muted-foreground">
          {tenant.name} · {app.name} app · {memories.length} memories under management
        </p>
      </div>

      {/* KPI grid */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        <KpiTile label="Memory MAU" value={kpis.memoryMau} format="number" icon={Users} delta="12%" />
        <KpiTile label="Memory Ops" value={kpis.memoryOps} format="number" icon={Zap} delta="8%" />
        <KpiTile label="Useful Rate" value={kpis.usefulRate} format="percent" icon={ThumbsUp} delta="2.1%" />
        <KpiTile label="False Rate" value={kpis.falseRate} format="percent" icon={AlertTriangle} delta="0.4%" deltaPositive={false} />
        <KpiTile label="Migrations OK" value={kpis.migrationSuccess} format="percent" icon={ArrowLeftRight} delta="1.2%" />
        <KpiTile label="Cross-Model Parity" value={kpis.crossModelParity} format="percent" icon={Shuffle} delta="0.03" />
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.6fr_1fr]">
        {/* Activity chart */}
        <Card>
          <CardHeader>
            <CardTitle>Memory activity</CardTitle>
            <CardDescription>Reads vs writes · last 7 days</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="mb-4 flex items-center gap-4 text-xs">
              <span className="flex items-center gap-1.5">
                <span className="size-2 rounded-full bg-chart-1" />
                <span className="text-muted-foreground">Reads</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className="size-2 rounded-full bg-chart-2" />
                <span className="text-muted-foreground">Writes</span>
              </span>
            </div>
            <ActivityChart />
          </CardContent>
        </Card>

        {/* Alerts */}
        <Card>
          <CardHeader>
            <CardTitle>Alerts</CardTitle>
            <CardDescription>Items needing attention</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {alerts.map((alert) => {
              const cfg = severityConfig[alert.severity];
              const Icon = cfg.icon;
              return (
                <div key={alert.id} className="flex items-start gap-3 rounded-lg border p-3">
                  <Icon className={`mt-0.5 size-4 shrink-0 ${cfg.color}`} strokeWidth={1.5} />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium leading-snug">{alert.title}</p>
                    <p className="mt-0.5 text-xs text-muted-foreground">{alert.detail}</p>
                    <p className="mt-1 text-[10px] text-muted-foreground/70">{formatRelativeDay(alert.timestamp)}</p>
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>
      </div>

      {/* Onboarding banner — only shows while quickstart incomplete (Stripe-style) */}
      <OnboardingBanner quickstart={quickstart} />

      {/* Migration demo (the wedge) + system health */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="overflow-hidden border-primary/30 bg-primary/[0.03]">
          <CardContent className="p-0">
            <div className="flex items-center gap-4 p-5">
              <div className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-primary/15">
                <ArrowLeftRight className="size-5 text-primary" strokeWidth={1.5} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-semibold">Try the migration demo</p>
                  <Badge variant="ink" className="text-[9px]">the wedge</Badge>
                </div>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  Walk the v1→v2 memory migration as a user would. The core proof of portability.
                </p>
              </div>
              <Button size="sm" asChild>
                <Link href="/app/migrate">
                  Try it
                  <ArrowRight className="size-3.5" />
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>System</span>
              <Badge variant="success" className="gap-1">
                <CheckCircle2 className="size-3" />
                Operational
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2.5 text-sm">
            <Row label="Ingest API" value="p99 · 84ms" ok />
            <Row label="Retrieve API" value="p99 · 142ms" ok />
            <Row label="Migration engine" value="idle · ready" ok />
            <Row label="Webhooks" value="2 subscribers" ok />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function OnboardingBanner({ quickstart }: { quickstart: { apiKeyCreated: boolean; testUserCreated: boolean; firstEventSent: boolean; firstRetrieveDone: boolean } }) {
  const steps = [
    { label: "API key", done: quickstart.apiKeyCreated },
    { label: "Test user", done: quickstart.testUserCreated },
    { label: "First event", done: quickstart.firstEventSent },
    { label: "Retrieve", done: quickstart.firstRetrieveDone },
  ];
  const doneCount = steps.filter((s) => s.done).length;
  const complete = doneCount === steps.length;
  const pct = (doneCount / steps.length) * 100;

  if (complete) return null;

  return (
    <Card className="border-primary/30 bg-primary/[0.03]">
      <CardContent className="p-5">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <Rocket className="size-4 text-primary" strokeWidth={1.5} />
              <p className="text-sm font-semibold">Get started — ship a memory loop in 2 hours</p>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              {doneCount} of {steps.length} steps complete. Send your first event to see a memory form.
            </p>
            <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5">
              {steps.map((s) => (
                <span key={s.label} className="inline-flex items-center gap-1.5 text-xs">
                  {s.done ? (
                    <CheckCircle2 className="size-3.5 text-emerald-500" strokeWidth={1.75} />
                  ) : (
                    <Circle className="size-3.5 text-muted-foreground/50" strokeWidth={1.75} />
                  )}
                  <span className={s.done ? "text-foreground" : "text-muted-foreground"}>{s.label}</span>
                </span>
              ))}
            </div>
          </div>
          <Button size="sm" asChild className="shrink-0">
            <Link href="/console/quickstart">
              Continue setup
              <ArrowRight className="size-3.5" />
            </Link>
          </Button>
        </div>
        {/* progress bar */}
        <div className="mt-4 h-1.5 w-full overflow-hidden rounded-full bg-muted">
          <div className="h-full rounded-full bg-primary transition-all duration-500" style={{ width: `${pct}%` }} />
        </div>
      </CardContent>
    </Card>
  );
}

function Row({ label, value, ok }: { label: string; value: string; ok?: boolean }) {
  return (
    <div className="flex items-center justify-between border-b pb-2.5 last:border-0 last:pb-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="flex items-center gap-2">
        <span className="tabular text-xs text-foreground/80">{value}</span>
        {ok && <span className="size-1.5 rounded-full bg-emerald-500" />}
      </span>
    </div>
  );
}
