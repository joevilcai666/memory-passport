"use client";

import {
  Cpu,
  RefreshCw,
  Download,
  MoreHorizontal,
  CircleCheck,
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
          <CircleCheck className="size-2.5" />
          Bound
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

// ---- Migration row helpers ------------------------------------------------

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
              <RefreshCw className="size-4" />
              Retry
            </DropdownMenuItem>
          )}
          <DropdownMenuItem
            onClick={() =>
              toast.success("Report exported", {
                description: `${row.moved} memories · JSON`,
              })
            }
          >
            <Download className="size-4" />
            Export report
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}

// ---- Page -----------------------------------------------------------------

export default function DevicesConsolePage() {
  const { devices, users, migration } = useMemoryStore();

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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="space-y-1.5">
        <h1 className="text-2xl font-medium tracking-tight">Devices</h1>
        <p className="text-sm text-muted-foreground">
          Device models, bindings, and migrations across your fleet.
        </p>
      </div>

      {/* Section 1 — Device models */}
      <Card>
        <CardHeader>
          <CardTitle>Device models</CardTitle>
          <CardDescription>
            Every unit paired to this app and its binding status.
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
                          <Cpu
                            className="size-3.5 text-primary"
                            strokeWidth={1.5}
                          />
                        </span>
                        {d.model}
                      </span>
                    </TableCell>
                    <TableCell>
                      {isV2 ? (
                        <Badge variant="ink" className="gap-1">
                          {d.generation}
                          <span className="rounded bg-ink-600/15 px-1 text-[10px] font-semibold">
                            New
                          </span>
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
                        <span className="text-sm">
                          {boundUser.display_name}
                        </span>
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

      {/* Section 2 — Recent migrations */}
      <Card>
        <CardHeader>
          <CardTitle>Recent migrations</CardTitle>
          <CardDescription>
            Memory transfers between device generations.
          </CardDescription>
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
                    row.id === migration.id &&
                      currentCompleted &&
                      "bg-emerald-500/5",
                  )}
                >
                  <TableCell className="pl-0 font-medium">
                    {row.userName}
                  </TableCell>
                  <TableCell>
                    <span className="font-mono text-xs tabular text-muted-foreground">
                      {row.sourceGen}
                    </span>
                  </TableCell>
                  <TableCell>
                    <span className="flex items-center gap-1.5">
                      <span className="font-mono text-xs tabular text-muted-foreground">
                        {row.targetGen}
                      </span>
                    </span>
                  </TableCell>
                  <TableCell className="font-mono text-sm tabular">
                    {row.moved}
                  </TableCell>
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
    </div>
  );
}

/** Build an ISO timestamp n days in the past for the historical rows. */
function migrationDaysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString();
}
