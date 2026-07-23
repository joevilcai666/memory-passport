"use client";

import * as React from "react";
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
  Loader2,
  Copy,
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useMemoryStore } from "@/store/memory-store";
import { cn, formatRelativeDay } from "@/lib/utils";
import { toast } from "sonner";
import type { AuditAction, TeamInviteCreateResult, TeamRole } from "@/lib/types";

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

const auditMeta: Partial<Record<AuditAction, AuditMeta>> = {
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
  "user.deleted": { label: "user.deleted", Icon: Trash2, tint: "bg-rose-500/10", color: "text-rose-600 dark:text-rose-400" },
};

function metaForAudit(action: AuditAction): AuditMeta {
  return auditMeta[action] ?? {
    label: action,
    Icon: History,
    tint: "bg-neutral-500/10",
    color: "text-neutral-600 dark:text-neutral-400",
  };
}

// ---- Page -----------------------------------------------------------------

export default function SettingsPage() {
  const { team, pendingInvites, auditLogs, dataMode, inviteTeamMember } = useMemoryStore();
  const [showInviteForm, setShowInviteForm] = React.useState(false);
  const [email, setEmail] = React.useState("");
  const [role, setRole] = React.useState<TeamRole>("Support");
  const [inviting, setInviting] = React.useState(false);
  const [issuedInvite, setIssuedInvite] = React.useState<{
    result: TeamInviteCreateResult;
    url: string;
  } | null>(null);
  const otherPendingInvites = pendingInvites.filter(
    (invite) => invite.id !== issuedInvite?.result.invite.id,
  );

  const handleInvite = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!email.trim() || inviting) return;
    setInviting(true);
    try {
      const result = await inviteTeamMember({ email: email.trim(), role });
      const url = `${window.location.origin}/invite/${result.token}`;
      setIssuedInvite({ result, url });
      setEmail("");
      try {
        await navigator.clipboard.writeText(url);
        toast.success("Invite link copied");
      } catch (error) {
        toast.error("Invite created, but the link could not be copied", {
          description: error instanceof Error ? error.message : "Clipboard unavailable",
        });
      }
    } catch (error) {
      toast.error("Invitation failed", {
        description: error instanceof Error ? error.message : "Unknown error",
      });
    } finally {
      setInviting(false);
    }
  };

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
                  onClick={() => setShowInviteForm((visible) => !visible)}
                  disabled={dataMode !== "live"}
                >
                  <UserPlus className="size-3.5" />
                  Invite member
                </Button>
              </CardAction>
            </CardHeader>
            <CardContent className="space-y-1">
              {showInviteForm && (
                <form onSubmit={handleInvite} className="mb-4 grid gap-3 rounded-lg border bg-muted/20 p-4 sm:grid-cols-[1fr_150px_auto] sm:items-end">
                  <div className="space-y-1.5">
                    <Label htmlFor="invite-email">Email</Label>
                    <Input
                      id="invite-email"
                      type="email"
                      value={email}
                      onChange={(event) => setEmail(event.target.value)}
                      placeholder="teammate@example.com"
                      required
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="invite-role">Role</Label>
                    <select
                      id="invite-role"
                      aria-label="Invite role"
                      value={role}
                      onChange={(event) => setRole(event.target.value as TeamRole)}
                      className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                    >
                      <option value="Admin">Admin</option>
                      <option value="Support">Support</option>
                    </select>
                  </div>
                  <Button type="submit" disabled={!email.trim() || inviting}>
                    {inviting ? <Loader2 className="size-3.5 animate-spin" /> : <UserPlus className="size-3.5" />}
                    {inviting ? "Creating invite..." : "Create invite"}
                  </Button>
                </form>
              )}

              {issuedInvite && (
                <div className="mb-4 rounded-lg border border-amber-500/40 bg-amber-500/5 p-4">
                  <p className="text-sm font-medium">Pending invitation</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {issuedInvite.result.invite.email} · {issuedInvite.result.invite.role}
                  </p>
                  <div className="mt-3 flex items-center gap-2">
                    <code className="min-w-0 flex-1 overflow-x-auto rounded bg-background px-2.5 py-2 font-mono text-[11px]">
                      {issuedInvite.url}
                    </code>
                    <Button
                      type="button"
                      variant="outline"
                      size="icon-sm"
                      aria-label="Copy invite link"
                      onClick={async () => {
                        try {
                          await navigator.clipboard.writeText(issuedInvite.url);
                          toast.success("Invite link copied");
                        } catch (error) {
                          toast.error("Could not copy invite link", {
                            description: error instanceof Error ? error.message : "Clipboard unavailable",
                          });
                        }
                      }}
                    >
                      <Copy className="size-3.5" />
                    </Button>
                  </div>
                </div>
              )}

              {otherPendingInvites.length > 0 && (
                <div className="mb-4 space-y-2 rounded-lg border p-4">
                  <p className="text-sm font-medium">Pending invites ({otherPendingInvites.length})</p>
                  {otherPendingInvites.map((invite) => (
                    <div key={invite.id} className="flex items-center justify-between gap-3 text-xs text-muted-foreground">
                      <span>{invite.email}</span>
                      <Badge variant="outline">{invite.role}</Badge>
                    </div>
                  ))}
                </div>
              )}

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
                  const meta = metaForAudit(log.action);
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
