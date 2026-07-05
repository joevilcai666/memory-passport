"use client";

import {
  Smartphone,
  Users,
  Shuffle,
  Globe,
  Check,
  Lock,
  ShieldCheck,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useMemoryStore } from "@/store/memory-store";
import { cn } from "@/lib/utils";
import type {
  AutoWriteRule,
  MemorySensitivity,
  MemoryType,
  Portability,
} from "@/lib/types";

// ---- Static config ---------------------------------------------------------

const typeDotColor: Record<MemoryType, string> = {
  profile: "bg-ink-600",
  preference: "bg-emerald-500",
  boundary: "bg-rose-500",
  relationship: "bg-violet-500",
  event: "bg-amber-500",
  task: "bg-neutral-500",
};

function capitalize(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

const sensitivityMeta: Record<MemorySensitivity, string> = {
  S0: "S0 · auto-write",
  S1: "S1 · auto-write + visible",
  S2: "S2 · user-confirm",
  S3: "S3 · block / safety",
};

const actionMeta: Record<
  "auto_write" | "confirm" | "block",
  { label: string; variant: "success" | "warning" | "destructive" }
> = {
  auto_write: { label: "Auto-write", variant: "success" },
  confirm: { label: "Confirm", variant: "warning" },
  block: { label: "Block", variant: "destructive" },
};

const MAX_MEMORIES_OPTIONS = [4, 6, 8, 12, 16];

// ---- Portability axis config ----------------------------------------------

type AxisKey = keyof Pick<
  Portability,
  "cross_device" | "cross_role" | "cross_model" | "cross_brand_app"
>;

interface AxisConfig {
  key: AxisKey;
  title: string;
  description: string;
  icon: typeof Smartphone;
}

const AXES: AxisConfig[] = [
  {
    key: "cross_device",
    title: "Cross-device",
    description: "Memories travel between Luna's devices (phone → robot).",
    icon: Smartphone,
  },
  {
    key: "cross_role",
    title: "Cross-role",
    description:
      "Core memories shared across the user's AI roles (companion, coach, pet).",
    icon: Users,
  },
  {
    key: "cross_model",
    title: "Cross-model",
    description:
      "Memories are retrievable across LLMs — no vendor lock-in. The moat.",
    icon: Shuffle,
  },
  {
    key: "cross_brand_app",
    title: "Cross-brand app",
    description:
      "Carry memories to a different brand's app. Architecture-ready, deferred to P2.",
    icon: Globe,
  },
];

// ---- Sub-components --------------------------------------------------------

function ActionBadge({ action }: { action: AutoWriteRule["action"] }) {
  const meta = actionMeta[action];
  return <Badge variant={meta.variant}>{meta.label}</Badge>;
}

function SensitivityBadge({ sensitivity }: { sensitivity: MemorySensitivity }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          className="font-mono text-xs tabular rounded-md border bg-muted/40 px-1.5 py-0.5 hover:bg-muted transition-colors cursor-help"
        >
          {sensitivity}
        </button>
      </TooltipTrigger>
      <TooltipContent>{sensitivityMeta[sensitivity]}</TooltipContent>
    </Tooltip>
  );
}

function AxisCard({
  config,
  checked,
  onToggle,
}: {
  config: AxisConfig;
  checked: boolean;
  onToggle: () => void;
}) {
  const Icon = config.icon;
  const isMoat = config.key === "cross_model";
  const isDeferred = config.key === "cross_brand_app";

  return (
    <div
      className={cn(
        "group relative flex items-start gap-4 rounded-xl border p-5 transition-colors",
        isMoat && "border-primary/20 bg-primary/5",
        isDeferred && "opacity-70",
      )}
    >
      <div
        className={cn(
          "flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10",
          isDeferred && "bg-muted",
        )}
      >
        <Icon
          className={cn(
            "size-5 text-primary",
            isDeferred && "text-muted-foreground",
          )}
          strokeWidth={1.5}
        />
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="text-sm font-medium leading-tight cursor-help">
                {config.title}
              </span>
            </TooltipTrigger>
            <TooltipContent>{config.title}</TooltipContent>
          </Tooltip>
          {isMoat && <Badge variant="ink">Moat</Badge>}
          {isDeferred && (
            <Badge variant="secondary" className="gap-1">
              <Lock className="size-2.5" />
              P2 · deferred
            </Badge>
          )}
        </div>
        <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
          {config.description}
        </p>
      </div>

      <div className="shrink-0 self-center">
        <Switch checked={checked} onCheckedChange={onToggle} disabled={isDeferred} />
      </div>
    </div>
  );
}

// ---- Page ------------------------------------------------------------------

export default function MemoryPolicyPage() {
  const policy = useMemoryStore((s) => s.policy);
  const togglePortabilityAxis = useMemoryStore((s) => s.togglePortabilityAxis);
  const setMaxMemoriesPerResponse = useMemoryStore(
    (s) => s.setMaxMemoriesPerResponse,
  );
  const toggleSensitiveInPrompt = useMemoryStore(
    (s) => s.toggleSensitiveInPrompt,
  );

  return (
    <TooltipProvider delayDuration={200}>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2.5">
              <h1 className="text-2xl font-medium tracking-tight">Memory Policy</h1>
              <Badge variant="outline" className="font-mono text-[11px] tabular">
                {policy.id}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              Defaults for how Luna writes, retrieves, and carries memory.
            </p>
          </div>

          <div className="flex items-center gap-1.5 text-xs text-muted-foreground md:pt-1.5">
            <Check className="size-3.5 text-emerald-500" strokeWidth={2.5} />
            <span>Auto-saved</span>
          </div>
        </div>

        {/* Section 1 — Auto-write rules */}
        <Card>
          <CardHeader>
            <CardTitle>Auto-write rules</CardTitle>
            <CardDescription>
              How each memory type is written. Sensitivity controls the safety flow.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className="pl-0">Memory Type</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Sensitivity</TableHead>
                  <TableHead className="pr-0 text-right">TTL</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {policy.auto_write_rules.map((rule) => (
                  <TableRow key={rule.id} className="h-[52px]">
                    <TableCell className="pl-0 font-medium">
                      <span className="flex items-center gap-2.5">
                        <span
                          className={cn(
                            "size-2 rounded-full",
                            typeDotColor[rule.memory_type],
                          )}
                        />
                        {capitalize(rule.memory_type)}
                      </span>
                    </TableCell>
                    <TableCell>
                      <ActionBadge action={rule.action} />
                    </TableCell>
                    <TableCell>
                      <SensitivityBadge sensitivity={rule.sensitivity} />
                    </TableCell>
                    <TableCell className="pr-0 text-right font-mono text-xs tabular text-muted-foreground">
                      {rule.ttl_days === null ? (
                        <span>No expiry</span>
                      ) : (
                        <span>{rule.ttl_days} days</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        {/* Section 2 — Portability */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Portability
              <Badge variant="ink" className="gap-1">
                <ShieldCheck className="size-3" />
                The 4 axes
              </Badge>
            </CardTitle>
            <CardDescription>
              Memory belongs to the user and travels with them — by architecture,
              not by promise.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 sm:grid-cols-2">
              {AXES.map((config) => (
                <AxisCard
                  key={config.key}
                  config={config}
                  checked={policy.portability[config.key]}
                  onToggle={() => togglePortabilityAxis(config.key)}
                />
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Section 3 — Retrieval */}
        <Card>
          <CardHeader>
            <CardTitle>Retrieval</CardTitle>
            <CardDescription>
              How memories are injected into model context.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-0">
            {/* Max memories per response */}
            <div className="flex items-center justify-between gap-4 py-4">
              <div className="min-w-0 space-y-1">
                <p className="text-sm font-medium leading-tight">
                  Max memories per response
                </p>
                <p className="text-xs text-muted-foreground">
                  Upper bound on memories injected into a single model context.
                </p>
              </div>
              <Select
                value={String(policy.retrieval.max_memories_per_response)}
                onValueChange={(v) => setMaxMemoriesPerResponse(Number(v))}
              >
                <SelectTrigger className="w-[88px] justify-center">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {MAX_MEMORIES_OPTIONS.map((n) => (
                    <SelectItem key={n} value={String(n)}>
                      <span className="font-mono tabular">{n}</span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <Separator />

            {/* Include sensitive memories in prompt */}
            <div className="flex items-start justify-between gap-4 py-4">
              <div className="min-w-0 flex-1 space-y-1">
                <p className="text-sm font-medium leading-tight">
                  Include sensitive memories in prompt
                </p>
                <p className="text-xs leading-relaxed text-muted-foreground">
                  Off by default. Sensitive memories (S2/S3) are masked unless
                  explicitly enabled.
                </p>
              </div>
              <div className="shrink-0 pt-0.5">
                <Switch
                  checked={policy.retrieval.include_sensitive_in_prompt}
                  onCheckedChange={toggleSensitiveInPrompt}
                />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </TooltipProvider>
  );
}
