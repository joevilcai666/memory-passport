"use client";

import * as React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  Cpu,
  Check,
  X,
  ThumbsUp,
  ThumbsDown,
  AlertTriangle,
  Shuffle,
} from "lucide-react";
import { toast } from "sonner";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useMemoryStore } from "@/store/memory-store";
import { cn, formatDateTime } from "@/lib/utils";
import type { Agent, MemoryRecord, RetrievalEvent, User } from "@/lib/types";

// ---- Config --------------------------------------------------------------

const REASONS = [
  "semantic match · 0.91",
  "scope match · 0.88",
  "temporal · 0.79",
  "boundary guard · 1.00",
];

// The PRD-canonical projection boilerplate that wraps the memory bullets.
const PROJECTION_HEADER = "Relevant long-term memories for this user:";
const PROJECTION_FOOTER =
  "Use these memories only when relevant. Do not mention that you have memory unless natural.";

// ---- Page ----------------------------------------------------------------

export default function MemoryTracePage() {
  const params = useParams<{ memoryId: string }>();
  const memoryId = params.memoryId;

  const memories = useMemoryStore((s) => s.memories);
  const currentUser = useMemoryStore((s) => s.currentUser);
  const agents = useMemoryStore((s) => s.agents);

  const memory = React.useMemo(
    () => memories.find((m) => m.id === memoryId),
    [memories, memoryId],
  );

  // The agent that did the retrieving.
  const agent: Agent | undefined = React.useMemo(
    () => (memory ? agents.find((a) => a.id === memory.agent_id) : undefined),
    [agents, memory],
  );

  // Latest retrieval event drives the "current request" framing.
  const latestRetrieval: RetrievalEvent | undefined = React.useMemo(() => {
    if (!memory?.model_provenance?.retrieval_history?.length) return undefined;
    return [...memory.model_provenance.retrieval_history].sort((a, b) =>
      a.timestamp < b.timestamp ? 1 : -1,
    )[0];
  }, [memory]);

  // The model that performed the latest retrieval — the cross-model moat label.
  const model = latestRetrieval?.model ?? memory?.model_provenance.created_by_model ?? "gpt-4o";

  // Sibling memories retrieved alongside this one (same user, active, portable).
  const retrievedSet: MemoryRecord[] = React.useMemo(() => {
    if (!memory) return [];
    const siblings = memories.filter(
      (m) =>
        m.user_id === memory.user_id &&
        m.id !== memory.id &&
        m.status === "active" &&
        m.portability.layer === "portable",
    );
    // Put the focus memory first, then 2-3 siblings.
    const siblingsTop = siblings.slice(0, 3);
    return [memory, ...siblingsTop];
  }, [memories, memory]);

  const projectionLines = React.useMemo(
    () => retrievedSet.map((m) => `- ${m.content}`),
    [retrievedSet],
  );

  // Cross-model parity from retrieval history.
  const retrievalHistory = React.useMemo<RetrievalEvent[]>(
    () => memory?.model_provenance.retrieval_history ?? [],
    [memory],
  );
  const distinctModels = React.useMemo(
    () => Array.from(new Set(retrievalHistory.map((h) => h.model))),
    [retrievalHistory],
  );
  // Per-model used aggregation (latest wins for display).
  const perModel = React.useMemo(() => {
    const map = new Map<string, { used: boolean; ts: string }>();
    for (const h of [...retrievalHistory].sort((a, b) =>
      a.timestamp < b.timestamp ? 1 : -1,
    )) {
      if (!map.has(h.model)) map.set(h.model, { used: h.used, ts: h.timestamp });
    }
    return map;
  }, [retrievalHistory]);
  const allConsistent =
    perModel.size > 1 &&
    Array.from(perModel.values()).every((v) => v.used === Array.from(perModel.values())[0].used);

  const userDisplay: User = currentUser;

  const recordFeedback = (msg: string) =>
    toast(msg, {
      description: `Feedback recorded for ${memory?.id ?? "this memory"}.`,
    });

  if (memory == null) {
    return (
      <div className="space-y-6">
        <Link
          href="/console/memory/debugger"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-3.5" />
          Debugger
        </Link>
        <Card>
          <CardContent className="p-10 text-center text-sm text-muted-foreground">
            Memory <span className="font-mono">{memoryId}</span> not found.
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="space-y-1.5">
        <Link
          href="/console/memory/debugger"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-3.5" />
          Debugger
        </Link>
        <div className="flex flex-wrap items-center gap-2.5">
          <h1 className="text-2xl font-medium tracking-tight">Memory Trace</h1>
          <Badge variant="outline" className="font-mono text-[11px] tabular">
            {memory.id}
          </Badge>
        </div>
        <p className="text-sm text-muted-foreground">
          A single retrieval request: what was found, what was projected, and which model did the
          retrieving.
        </p>
      </div>

      {/* Request info */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Request</CardTitle>
          <CardDescription>The retrieval context for this turn.</CardDescription>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-4">
            <Meta label="User" value={userDisplay.display_name} />
            <Meta
              label="Agent"
              value={
                agent ? (
                  <span className="inline-flex items-center gap-1.5">
                    <span>{agent.emoji}</span>
                    <span>{agent.name}</span>
                  </span>
                ) : (
                  "—"
                )
              }
            />
            <Meta
              label="Model"
              value={
                <Badge
                  variant="ink"
                  className="gap-1 font-mono text-[11px] tabular"
                >
                  <Cpu className="size-3" strokeWidth={2} />
                  {model}
                </Badge>
              }
              emphasize
            />
            <Meta
              label="Time"
              value={
                latestRetrieval ? (
                  <span className="font-mono text-xs tabular text-muted-foreground">
                    {formatDateTime(latestRetrieval.timestamp)}
                  </span>
                ) : (
                  <span className="text-xs text-muted-foreground">—</span>
                )
              }
            />
          </dl>
        </CardContent>
      </Card>

      {/* User message */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">User message</CardTitle>
          <CardDescription>The message that triggered retrieval.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex justify-end">
            <p className="max-w-[80%] rounded-2xl rounded-tr-sm bg-primary/10 px-3.5 py-2.5 text-sm leading-relaxed text-foreground">
              how should I talk to Mia tonight?
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Retrieved memories */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">
            Retrieved memories{" "}
            <span className="font-mono text-sm tabular text-muted-foreground">
              ({retrievedSet.length})
            </span>
          </CardTitle>
          <CardDescription>
            Ranked by relevance to the user message. The focus memory is marked as used.
          </CardDescription>
        </CardHeader>
        <CardContent className="px-0 pb-0">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead className="pl-6 w-[44px]">#</TableHead>
                <TableHead>Memory</TableHead>
                <TableHead className="w-[180px]">Why</TableHead>
                <TableHead className="pr-6 w-[90px] text-right">Used?</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {retrievedSet.map((m, i) => {
                const isFocus = m.id === memory.id;
                const used = isFocus
                  ? latestRetrieval?.used ?? true
                  : i < 3; // prototype: top-3 siblings treated as used
                return (
                  <TableRow key={m.id}>
                    <TableCell className="pl-6 font-mono text-xs tabular text-muted-foreground">
                      {i + 1}
                    </TableCell>
                    <TableCell>
                      <span
                        className={cn(
                          "block max-w-[440px] truncate text-sm",
                          isFocus ? "font-medium" : "font-normal",
                        )}
                        title={m.content}
                      >
                        {m.content}
                      </span>
                      <span className="text-[11px] text-muted-foreground">
                        {m.id} · {m.type}
                      </span>
                    </TableCell>
                    <TableCell>
                      <span className="font-mono text-[11px] tabular text-muted-foreground">
                        {REASONS[i % REASONS.length]}
                      </span>
                    </TableCell>
                    <TableCell className="pr-6 text-right">
                      {used ? (
                        <Check
                          className="ml-auto size-4 text-emerald-500"
                          strokeWidth={2.5}
                        />
                      ) : (
                        <X className="ml-auto size-4 text-muted-foreground" strokeWidth={2.5} />
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Projection */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Projection sent to model</CardTitle>
          <CardDescription>
            The exact block injected into <span className="font-mono">{model}</span>&apos;s context.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <pre className="overflow-x-auto rounded-lg bg-neutral-950 p-4 font-mono text-xs leading-relaxed text-neutral-100">
            <code>
              {PROJECTION_HEADER}
              {"\n"}
              {projectionLines.join("\n")}
              {"\n"}
              {PROJECTION_FOOTER}
            </code>
          </pre>
        </CardContent>
      </Card>

      {/* Feedback */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Was this retrieval good?</CardTitle>
          <CardDescription>
            Feedback tunes ranking and feeds the cross-model parity signal.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={() => recordFeedback("Feedback recorded: Useful")}>
              <ThumbsUp className="size-4" />
              Useful
            </Button>
            <Button variant="outline" size="sm" onClick={() => recordFeedback("Feedback recorded: Not useful")}>
              <ThumbsDown className="size-4" />
              Not useful
            </Button>
            <Button variant="outline" size="sm" onClick={() => recordFeedback("Feedback recorded: Wrong memory")}>
              <AlertTriangle className="size-4" />
              Wrong memory
            </Button>
            <Button variant="outline" size="sm" onClick={() => recordFeedback("Feedback recorded: Should not have used")}>
              <X className="size-4" />
              Should not have used
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Cross-model parity */}
      <Card className="border-ink-600/30 bg-ink-600/5">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Shuffle className="size-4 text-primary" strokeWidth={1.75} />
            Cross-model parity
            {distinctModels.length >= 2 && (
              <Badge variant="ink" className="gap-1">
                <Check className="size-3" strokeWidth={2.5} />
                {allConsistent ? "consistent" : "divergent"}
              </Badge>
            )}
          </CardTitle>
          <CardDescription>
            The same memory, retrieved across models. Portability is proven by parity, not by
            promise.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {retrievalHistory.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No cross-model retrieval history yet for this memory.
            </p>
          ) : (
            <div className="overflow-hidden rounded-lg border border-border/60">
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead className="pl-4">Model</TableHead>
                    <TableHead className="w-[120px]">Used</TableHead>
                    <TableHead className="pr-4 w-[200px] text-right">Timestamp</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {[...retrievalHistory]
                    .sort((a, b) => (a.timestamp < b.timestamp ? 1 : -1))
                    .map((h, i) => (
                      <TableRow key={`${h.model}-${h.timestamp}-${i}`}>
                        <TableCell className="pl-4">
                          <Badge variant="ink" className="gap-1 font-mono text-[11px] tabular">
                            <Cpu className="size-3" strokeWidth={2} />
                            {h.model}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {h.used ? (
                            <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-600 dark:text-emerald-400">
                              <Check className="size-3.5" strokeWidth={2.5} />
                              used
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                              <X className="size-3.5" strokeWidth={2.5} />
                              not used
                            </span>
                          )}
                        </TableCell>
                        <TableCell className="pr-4 text-right font-mono text-[11px] tabular text-muted-foreground">
                          {formatDateTime(h.timestamp)}
                        </TableCell>
                      </TableRow>
                    ))}
                </TableBody>
              </Table>
            </div>
          )}

          {distinctModels.length >= 2 && (
            <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
              This memory was also retrieved by{" "}
              {Array.from(perModel.keys())
                .map(
                  (mdl) =>
                    `${mdl} (${perModel.get(mdl)?.used ? "✓ used" : "✕ not used"})`,
                )
                .join(" and ")}
              . Parity:{" "}
              <span
                className={cn(
                  "font-medium",
                  allConsistent
                    ? "text-emerald-600 dark:text-emerald-400"
                    : "text-amber-600 dark:text-amber-400",
                )}
              >
                {allConsistent ? "consistent" : "divergent"}
              </span>
              .
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ---- Meta cell -----------------------------------------------------------

function Meta({
  label,
  value,
  emphasize,
}: {
  label: string;
  value: React.ReactNode;
  emphasize?: boolean;
}) {
  return (
    <div className={cn("space-y-1", emphasize && "rounded-lg bg-primary/5 p-2 -m-2")}>
      <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="text-sm font-medium">{value}</dd>
    </div>
  );
}
