"use client";

import {
  UserPlus,
  ShieldCheck,
  Plus,
  Pencil,
  Eye,
  Trash2,
  Smartphone,
  History,
  Download,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  CardAction,
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useMemoryStore } from "@/store/memory-store";
import { cn, formatRelativeDay } from "@/lib/utils";
import { toast } from "sonner";
import type { AuditAction, TeamRole } from "@/lib/types";

// ---- Helpers --------------------------------------------------------------

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? "")
    .join("");
}

const roleVariant: Record<
  TeamRole,
  "default" | "secondary" | "outline"
> = {
  Owner: "default",
  Admin: "secondary",
  Support: "outline",
};

// ---- Audit log styling ----------------------------------------------------

interface AuditMeta {
  label: string;
  /** tinted tile background + icon stroke color, keyed off the action family */
  Icon: typeof Plus;
  tint: string;
  color: string;
}

const auditMeta: Record<AuditAction, AuditMeta> = {
  "memory.created": { label: "memory.created", Icon: Plus, tint: "bg-emerald-500/10", color: "text-emerald-600 dark:text-emerald-400" },
  "memory.edited": { label: "memory.edited", Icon: Pencil, tint: "bg-ink-600/10", color: "text-ink-700 dark:text-ink-300" },
  "memory.deleted": { label: "memory.deleted", Icon: Trash2, tint: "bg-rose-500/10", color: "text-rose-600 dark:text-rose-400" },
  "memory.viewed": { label: "memory.viewed", Icon: Eye, tint: "bg-neutral-500/10", color: "text-neutral-600 dark:text-neutral-400" },
  "policy.changed": { label: "policy.changed", Icon: ShieldCheck, tint: "bg-ink-600/10", color: "text-ink-700 dark:text-ink-300" },
  "device.bound": { label: "device.bound", Icon: Smartphone, tint: "bg-neutral-500/10", color: "text-neutral-600 dark:text-neutral-400" },
  "device.unbound": { label: "device.unbound", Icon: Smartphone, tint: "bg-neutral-500/10", color: "text-neutral-600 dark:text-neutral-400" },
  "migration.started": { label: "migration.started", Icon: History, tint: "bg-emerald-500/10", color: "text-emerald-600 dark:text-emerald-400" },
  "migration.completed": { label: "migration.completed", Icon: History, tint: "bg-emerald-500/10", color: "text-emerald-600 dark:text-emerald-400" },
  "memory.exported": { label: "memory.exported", Icon: Download, tint: "bg-amber-500/10", color: "text-amber-600 dark:text-amber-400" },
};

// ---- Page -----------------------------------------------------------------

export default function SettingsPage() {
  const { team, auditLogs } = useMemoryStore();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="space-y-1.5">
        <h1 className="text-2xl font-medium tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground">Team and audit.</p>
      </div>

      <Tabs defaultValue="team">
        <TabsList>
          <TabsTrigger value="team">
            <UserPlus className="size-3.5" />
            Team
          </TabsTrigger>
          <TabsTrigger value="audit">
            <History className="size-3.5" />
            Audit log
          </TabsTrigger>
        </TabsList>

        {/* ---- Team tab ---- */}
        <TabsContent value="team">
          <Card>
            <CardHeader>
              <CardTitle>Team members</CardTitle>
              <CardDescription>
                {team.length} members with access to this tenant.
              </CardDescription>
              <CardAction>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    toast("Invite link copied", {
                      description: "Share it with your teammate.",
                    })
                  }
                >
                  <UserPlus className="size-3.5" />
                  Invite member
                </Button>
              </CardAction>
            </CardHeader>
            <CardContent className="space-y-1">
              {team.map((m, i) => (
                <div
                  key={m.id}
                  className={cn(
                    "flex items-center gap-3 py-3",
                    i !== team.length - 1 && "border-b",
                  )}
                >
                  <Avatar className="size-9">
                    <AvatarFallback
                      className="text-xs font-medium text-white"
                      style={{ backgroundColor: m.avatar_color }}
                    >
                      {initials(m.name)}
                    </AvatarFallback>
                  </Avatar>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{m.name}</span>
                      <Badge variant={roleVariant[m.role]}>{m.role}</Badge>
                    </div>
                    <p className="mt-0.5 truncate font-mono text-xs tabular text-muted-foreground">
                      {m.email}
                    </p>
                  </div>
                  <p className="shrink-0 text-[11px] text-muted-foreground/70">
                    last active {formatRelativeDay(m.last_active)}
                  </p>
                </div>
              ))}

              <p className="pt-4 text-xs text-muted-foreground/80">
                V0.1 roles: Owner · Admin · Support. Support cannot change
                policy.
              </p>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ---- Audit log tab ---- */}
        <TabsContent value="audit">
          <Card>
            <CardHeader>
              <CardTitle>Audit log</CardTitle>
              <CardDescription>
                Append-only record of every privileged action.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ol className="space-y-0">
                {auditLogs.map((log, i) => {
                  const meta = auditMeta[log.action];
                  const Icon = meta.Icon;
                  return (
                    <li
                      key={log.id}
                      className={cn(
                        "flex items-start gap-3 py-3",
                        i !== auditLogs.length - 1 && "border-b",
                      )}
                    >
                      {/* tinted icon tile */}
                      <span
                        className={cn(
                          "mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-md",
                          meta.tint,
                        )}
                      >
                        <Icon
                          className={cn("size-3.5", meta.color)}
                          strokeWidth={1.75}
                        />
                      </span>

                      {/* body */}
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                          <span className="text-sm font-medium">{log.actor}</span>
                          <Badge
                            variant="outline"
                            className="font-mono text-[10px] tabular"
                          >
                            {meta.label}
                          </Badge>
                          <span className="font-mono text-[11px] tabular text-muted-foreground/70">
                            → {log.target}
                          </span>
                        </div>
                        <p className="mt-0.5 text-sm text-muted-foreground">
                          {log.detail}
                        </p>
                      </div>

                      {/* timestamp */}
                      <span className="shrink-0 pt-0.5 text-right font-mono text-[11px] tabular text-muted-foreground/70">
                        {formatRelativeDay(log.timestamp)}
                      </span>
                    </li>
                  );
                })}
              </ol>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
