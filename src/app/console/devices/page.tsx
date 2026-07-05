"use client";

import Link from "next/link";
import {
  Cpu,
  RefreshCw,
  Download,
  MoreHorizontal,
  CircleCheck,
  ArrowLeftRight,
  TrendingUp,
  ShieldCheck,
  ArrowRight,
  Smartphone,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useMemoryStore } from "@/store/memory-store";
import { cn, formatRelativeDay } from "@/lib/utils";
import { toast } from "sonner";
import type { DeviceStatus } from "@/lib/types";

// ---- Status badge ---------------------------------------------------------

function DeviceStatusBadge({ status }: { status: DeviceStatus }) {
  switch (status) {
    case "bound":
      return (
        <Badge variant="success" className="gap-1">
          <CircleCheck className="size-2.5" /> Bound
        </Badge>
      );
    case "registered":
      return <Badge variant="secondary">Registered</Badge>;
    case "unbound":
      return <Badge variant="outline">Unbound</Badge>;
    case "wiped":
      return <Badge variant="destructive">Wiped</Badge>;
    default:
      return <Badge variant="outline">{status}</Badge>;
  }
}

// ---- Migration helpers ----------------------------------------------------

interface MigrationRow {
  id: string;
  userName: string;
  sourceGen: string;
  targetGen: string;
  moved: number;
  status: "preview" | "completed" | "failed";
  time: string;
}

function MigrationStatusBadge({ status }: { status: MigrationRow["status"] }) {
  switch (status) {
    case "completed":
      return <Badge variant="success">Completed</Badge>;
    case "failed":
      return <Badge variant="destructive">Failed</Badge>;
    case "preview":
      return <Badge variant="outline">Preview</Badge>;
    default:
      return <Badge variant="outline">{status}</Badge>;
  }
}

function MigrationActions({ row }: { row: MigrationRow }) {
  const canRetry = row.status === "failed" || row.status === "completed";
  return (
    <div className="flex justify-end">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon-sm" aria-label="Migration actions">
            <MoreHorizontal className="size-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          {canRetry && (
            <DropdownMenuItem
              onClick={() =>
                toast("Retry queued", {
                  description: `${row.userName} · ${row.sourceGen} → ${row.targetGen}`,
                })
              }
            >
              <RefreshCw className="size-4" /> Retry
            </DropdownMenuItem>
          )}
          <DropdownMenuItem
            onClick={() =>
              toast.success("Report exported", { description: `${row.moved} memories · JSON` })
            }
          >
            <Download className="size-4" /> Export report
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}

// ---- Page -----------------------------------------------------------------

export default function DevicesConsolePage() {
  const { devices, users, migration, app } = useMemoryStore();

  const userById = (id: string | null) =>
    id ? users.find((u) => u.id === id) : undefined;

  const sourceDevice = devices.find((d) => d.id === migration.source_device_id);
  const targetDevice = devices.find((d) => d.id === migration.target_device_id);
  const migrationUser = users.find((u) => u.id === migration.user_id);

  const rows: MigrationRow[] = [
    {
      id: migration.id,
      userName: migrationUser?.display_name ?? "—",
      sourceGen: sourceDevice?.generation ?? "—",
      targetGen: targetDevice?.generation ?? "—",
      moved: migration.selected_memory_ids.length,
      status:
        migration.status === "completed"
          ? "completed"
          : migration.status === "failed"
            ? "failed"
            : "preview",
      time: migration.created_at,
    },
    {
      id: "mig_hist_alex",
      userName: "Alex Rivera",
      sourceGen: "v1",
      targetGen: "v2",
      moved: 28,
      status: "completed",
      time: migrationDaysAgo(2),
    },
    {
      id: "mig_hist_sam",
      userName: "Sam Okafor",
      sourceGen: "v1",
      targetGen: "v2",
      moved: 12,
      status: "failed",
      time: migrationDaysAgo(5),
    },
  ];

  const currentCompleted = migration.status === "completed";
  const boundCount = devices.filter((d) => d.status === "bound").length;
  const completedMigrations = rows.filter((r) => r.status === "completed").length;
  const totalMigrations = rows.length;
  const retentionRate = totalMigrations > 0 ? completedMigrations / totalMigrations : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="space-y-1.5">
        <div className="flex flex-wrap items-center gap-2.5">
          <h1 className="text-2xl font-medium tracking-tight">Devices</h1>
          <Badge variant="outline" className="text-[10px]">
            {app.product_type === "software" ? "Software" : app.product_type === "hybrid" ? "Hybrid" : "Hardware"}
          </Badge>
        </div>
        <p className="text-sm text-muted-foreground">
          How memories move across device generations. The wedge that proves portability.
        </p>
      </div>

      {/* Migration health — what hardware customers actually care about */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <HealthTile
          icon={ArrowLeftRight}
          label="Migration success"
          value={`${(retentionRate * 100).toFixed(0)}%`}
          sub={`${completedMigrations}/${totalMigrations} recent`}
          tone="emerald"
        />
        <HealthTile
          icon={TrendingUp}
          label="Memory retention"
          value="98.1%"
          sub="across v1→v2 moves"
          tone="ink"
        />
        <HealthTile
          icon={Smartphone}
          label="Devices bound"
          value={String(boundCount)}
          sub={`${devices.length} registered`}
          tone="neutral"
        />
        <HealthTile
          icon={ShieldCheck}
          label="Resale-safe wipes"
          value="3"
          sub="tombstone verified"
          tone="neutral"
        />
      </div>

      {/* Generation upgrade path — the strategic narrative */}
      <Card className="border-primary/30 bg-primary/[0.03]">
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div>
              <CardTitle className="flex items-center gap-2">
                <ArrowLeftRight className="size-4 text-primary" strokeWidth={1.75} />
                Generation upgrade path
              </CardTitle>
              <CardDescription className="mt-1">
                When a user upgrades hardware, their relationship memory follows. This is the core selling point for hardware products.
              </CardDescription>
            </div>
            <Button size="sm" asChild className="shrink-0">
              <Link href="/app/migrate">
                Preview a migration
                <ArrowRight className="size-3.5" />
              </Link>
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {/* Visual flow: v1 → migration engine → v2 */}
          <div className="flex flex-col items-stretch gap-3 sm:flex-row sm:items-center">
            <GenerationCard gen="v1" label="Luna Robot v1" state="current" />
            <div className="flex flex-1 flex-col items-center gap-1 px-2 py-3 sm:py-0">
              <div className="flex items-center gap-2 text-xs font-medium text-primary">
                <ArrowLeftRight className="size-3.5" strokeWidth={1.75} />
                Migration engine
              </div>
              <p className="text-center text-[11px] text-muted-foreground">
                portable ✓ travels · device-local ✕ stays
              </p>
            </div>
            <GenerationCard
              gen="v2"
              label="Luna Robot v2"
              state={currentCompleted ? "active" : "pending"}
            />
          </div>
          {currentCompleted && (
            <div className="mt-4 flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-3 text-sm">
              <CircleCheck className="size-4 text-emerald-500" />
              <span>
                <span className="font-medium">{migrationUser?.display_name}</span>&apos;s
                relationship migrated to v2 — {migration.selected_memory_ids.length} memories inherited.
              </span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Recent migrations */}
      <Card>
        <CardHeader>
          <CardTitle>Recent migrations</CardTitle>
          <CardDescription>Memory transfers between device generations.</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead className="pl-0">User</TableHead>
                <TableHead>Source</TableHead>
                <TableHead>Target</TableHead>
                <TableHead>Memories moved</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Time</TableHead>
                <TableHead className="pr-0 text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((row) => (
                <TableRow
                  key={row.id}
                  className={cn(
                    "h-[52px]",
                    row.id === migration.id && currentCompleted && "bg-emerald-500/5",
                  )}
                >
                  <TableCell className="pl-0 font-medium">{row.userName}</TableCell>
                  <TableCell>
                    <Badge variant="secondary" className="font-mono text-xs">{row.sourceGen}</Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant="ink" className="font-mono text-xs">{row.targetGen}</Badge>
                  </TableCell>
                  <TableCell className="font-mono text-sm tabular">{row.moved}</TableCell>
                  <TableCell>
                    <MigrationStatusBadge status={row.status} />
                  </TableCell>
                  <TableCell className="font-mono text-xs tabular text-muted-foreground">
                    {formatRelativeDay(row.time)}
                  </TableCell>
                  <TableCell className="pr-0">
                    <MigrationActions row={row} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Device registry — supporting context (lifecycle / compliance) */}
      <Card>
        <CardHeader>
          <CardTitle>Device registry</CardTitle>
          <CardDescription>
            Lifecycle state of every unit. Bound, unbound, or wiped (resale-safe).
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead className="pl-0">Model</TableHead>
                <TableHead>Generation</TableHead>
                <TableHead>Serial</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Bound user</TableHead>
                <TableHead className="pr-0 text-right">Last seen</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {devices.map((d) => {
                const boundUser = userById(d.bound_user_id);
                const isV2 = d.generation === "v2";
                return (
                  <TableRow key={d.id} className="h-[52px]">
                    <TableCell className="pl-0">
                      <span className="flex items-center gap-2.5 font-medium">
                        <span className="flex size-7 shrink-0 items-center justify-center rounded-md bg-primary/10">
                          <Cpu className="size-3.5 text-primary" strokeWidth={1.5} />
                        </span>
                        {d.model}
                      </span>
                    </TableCell>
                    <TableCell>
                      {isV2 ? (
                        <Badge variant="ink" className="gap-1">
                          {d.generation}
                          <span className="rounded bg-ink-600/15 px-1 text-[10px] font-semibold">New</span>
                        </Badge>
                      ) : (
                        <Badge variant="secondary">{d.generation}</Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      <span className="font-mono text-xs tabular text-muted-foreground">
                        {d.serial_number_hash}
                      </span>
                    </TableCell>
                    <TableCell>
                      <DeviceStatusBadge status={d.status} />
                    </TableCell>
                    <TableCell>
                      {boundUser ? (
                        <span className="text-sm">{boundUser.display_name}</span>
                      ) : (
                        <span className="text-sm text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell className="pr-0 text-right font-mono text-xs tabular text-muted-foreground">
                      {d.last_seen_at ? formatRelativeDay(d.last_seen_at) : "—"}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

// ---- Health tile ----------------------------------------------------------

function HealthTile({
  icon: Icon,
  label,
  value,
  sub,
  tone,
}: {
  icon: typeof Cpu;
  label: string;
  value: string;
  sub: string;
  tone: "emerald" | "ink" | "neutral";
}) {
  const toneClass = {
    emerald: "text-emerald-600 dark:text-emerald-400",
    ink: "text-primary",
    neutral: "text-foreground",
  }[tone];
  return (
    <div className="rounded-xl border bg-card p-4">
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">{label}</span>
        <Icon className={cn("size-3.5", toneClass)} strokeWidth={1.5} />
      </div>
      <p className={cn("mt-1.5 text-xl font-semibold tabular", toneClass)}>{value}</p>
      <p className="mt-0.5 text-[11px] text-muted-foreground">{sub}</p>
    </div>
  );
}

// ---- Generation card (the upgrade flow visual) ---------------------------

function GenerationCard({
  gen,
  label,
  state,
}: {
  gen: string;
  label: string;
  state: "current" | "pending" | "active";
}) {
  const stateConfig = {
    current: { badge: "Current", variant: "secondary" as const, ring: "" },
    pending: { badge: "Awaiting", variant: "outline" as const, ring: "border-dashed" },
    active: { badge: "Active", variant: "success" as const, ring: "border-emerald-500/40 bg-emerald-500/5" },
  }[state];

  return (
    <div className={cn("flex-1 rounded-xl border p-4", stateConfig.ring)}>
      <div className="flex items-center justify-between">
        <span className="flex size-9 items-center justify-center rounded-lg bg-primary/10">
          <Cpu className="size-4 text-primary" strokeWidth={1.5} />
        </span>
        <Badge variant={stateConfig.variant} className="text-[10px]">{stateConfig.badge}</Badge>
      </div>
      <p className="mt-3 text-sm font-medium">{label}</p>
      <p className="font-mono text-[11px] tabular text-muted-foreground">{gen}</p>
    </div>
  );
}

/** Build an ISO timestamp n days in the past for the historical rows. */
function migrationDaysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString();
}
