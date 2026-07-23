"use client";

import * as React from "react";
import {
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
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
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
import type { Agent, RetrievalEvent, TraceFeedbackCategory } from "@/lib/types";

const PROJECTION_HEADER = "Relevant long-term memories for this user:";
const PROJECTION_FOOTER =
  "Use these memories only when relevant. Do not mention that you have memory unless natural.";

/**
 * MemoryTraceSheet — the trace rendered as a right-side drawer.
 *
 * Clicking a memory row opens this instead of navigating away, so the user
 * list / table context is preserved. Mirrors the PRD §5.1.6 trace content:
 * request info (Model labeled), retrieved memories, projection, feedback,
 * cross-model parity.
 */
export function MemoryTraceSheet({
  memoryId,
  open,
  onOpenChange,
}: {
  memoryId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const memories = useMemoryStore((s) => s.memories);
  const currentUser = useMemoryStore((s) => s.currentUser);
  const agents = useMemoryStore((s) => s.agents);
  const lastTraceId = useMemoryStore((s) => s.lastTraceId);
  const storedTrace = useMemoryStore((s) => s.lastTrace);
  const recordTraceFeedback = useMemoryStore((s) => s.recordTraceFeedback);
  const [feedbackSelection, setFeedbackSelection] = React.useState<{
    traceId: string;
    memoryId: string;
    category: TraceFeedbackCategory;
  } | null>(null);
  const [savingFeedback, setSavingFeedback] = React.useState<TraceFeedbackCategory | null>(null);

  const memory = React.useMemo(
    () => memories.find((m) => m.id === memoryId),
    [memories, memoryId],
  );

  const agent: Agent | undefined = React.useMemo(
    () => (memory ? agents.find((a) => a.id === memory.agent_id) : undefined),
    [agents, memory],
  );

  const latestRetrieval: RetrievalEvent | undefined = React.useMemo(() => {
    if (!memory?.model_provenance?.retrieval_history?.length) return undefined;
    return [...memory.model_provenance.retrieval_history].sort((a, b) =>
      a.timestamp < b.timestamp ? 1 : -1,
    )[0];
  }, [memory]);

  const trace = storedTrace?.id === lastTraceId ? storedTrace : null;
  const model =
    (typeof trace?.caller.model === "string" ? trace.caller.model : null) ??
    latestRetrieval?.model ??
    memory?.model_provenance.created_by_model ??
    "unknown";

  const retrievedSet = trace?.projected.results ?? [];
  const memoryWasProjected =
    memory != null && retrievedSet.some((result) => result.id === memory.id);
  const projectionLines = retrievedSet.map((result) =>
    `- ${result.content ?? `[${result.id}]`}`,
  );

  const retrievalHistory = React.useMemo<RetrievalEvent[]>(
    () => memory?.model_provenance.retrieval_history ?? [],
    [memory],
  );
  const distinctModels = React.useMemo(
    () => Array.from(new Set(retrievalHistory.map((h) => h.model))),
    [retrievalHistory],
  );
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
    Array.from(perModel.values()).every(
      (v) => v.used === Array.from(perModel.values())[0].used,
    );

  const localSelectedFeedback =
    feedbackSelection?.traceId === lastTraceId &&
    feedbackSelection.memoryId === memoryId
      ? feedbackSelection.category
      : null;
  const persistedFeedback =
    trace?.feedback?.memory_id === memoryId ? trace.feedback.category : null;
  const selectedFeedback = localSelectedFeedback ?? persistedFeedback;
  const feedbackUnavailableReason = !lastTraceId
    ? "Run a retrieve test first to create a real trace for feedback."
    : !trace
      ? "The trace details are unavailable; run the retrieve test again."
      : !memoryWasProjected
        ? "This memory was not projected by the loaded trace."
        : null;

  const recordFeedback = async (category: TraceFeedbackCategory) => {
    if (!memory || !lastTraceId || !memoryWasProjected || savingFeedback) return;
    setSavingFeedback(category);
    try {
      const trace = await recordTraceFeedback(lastTraceId, {
        memory_id: memory.id,
        category,
      });
      setFeedbackSelection({
        traceId: lastTraceId,
        memoryId: memory.id,
        category: trace.feedback?.category ?? category,
      });
      toast.success("Feedback recorded");
    } catch (error) {
      toast.error("Feedback could not be recorded", {
        description: error instanceof Error ? error.message : "Unknown error",
      });
    } finally {
      setSavingFeedback(null);
    }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full overflow-y-auto ds-scroll sm:max-w-xl"
      >
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            Memory trace
            {memory && (
              <Badge variant="outline" className="font-mono text-[11px] tabular">
                {memory.id}
              </Badge>
            )}
          </SheetTitle>
          <SheetDescription>
            A single retrieval request: what was found, what was projected, and
            which model did the retrieving.
          </SheetDescription>
        </SheetHeader>

        {memory == null ? (
          <div className="px-6 py-10 text-center text-sm text-muted-foreground">
            Select a memory to view its trace.
          </div>
        ) : (
          <div className="space-y-5 px-4 pb-8">
            {/* Request info */}
            <div className="rounded-xl border p-4">
              <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Request
              </p>
              <dl className="grid grid-cols-2 gap-x-4 gap-y-3">
                <Meta label="User" value={currentUser.display_name} />
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
                    <Badge variant="ink" className="gap-1 font-mono text-[11px] tabular">
                      <Cpu className="size-3" strokeWidth={2} />
                      {model}
                    </Badge>
                  }
                  emphasize
                />
                <Meta
                  label="Time"
                  value={
                    trace ? (
                      <span className="font-mono text-xs tabular text-muted-foreground">
                        {formatDateTime(trace.created_at)}
                      </span>
                    ) : (
                      <span className="text-xs text-muted-foreground">—</span>
                    )
                  }
                />
              </dl>
            </div>

            {/* User message */}
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                User message
              </p>
              <div className="flex justify-end">
                <p className="max-w-[85%] rounded-2xl rounded-tr-sm bg-primary/10 px-3.5 py-2.5 text-sm leading-relaxed">
                  {trace?.query ?? "No live retrieval query is loaded."}
                </p>
              </div>
            </div>

            {/* Retrieved memories */}
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Retrieved memories{" "}
                <span className="font-mono tabular">({retrievedSet.length})</span>
              </p>
              <div className="overflow-hidden rounded-lg border">
                <Table>
                  <TableHeader>
                    <TableRow className="hover:bg-transparent">
                      <TableHead className="pl-3 w-[32px]">#</TableHead>
                      <TableHead>Memory</TableHead>
                      <TableHead className="w-[120px]">Why</TableHead>
                      <TableHead className="pr-3 w-[60px] text-right">Used?</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {retrievedSet.map((m, i) => {
                      const isFocus = m.id === memory.id;
                      const used = true;
                      return (
                        <TableRow key={m.id}>
                          <TableCell className="pl-3 font-mono text-xs tabular text-muted-foreground">
                            {i + 1}
                          </TableCell>
                          <TableCell>
                            <span
                              className={cn(
                                "block max-w-[220px] truncate text-sm",
                                isFocus ? "font-medium" : "font-normal",
                              )}
                              title={m.content}
                            >
                              {m.content}
                            </span>
                          </TableCell>
                          <TableCell>
                            <span className="font-mono text-[10px] tabular text-muted-foreground">
                              projected
                            </span>
                          </TableCell>
                          <TableCell className="pr-3 text-right">
                            {used ? (
                              <Check className="ml-auto size-3.5 text-emerald-500" strokeWidth={2.5} />
                            ) : (
                              <X className="ml-auto size-3.5 text-muted-foreground" strokeWidth={2.5} />
                            )}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            </div>

            {/* Projection */}
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Projection sent to model
              </p>
              <pre className="overflow-x-auto rounded-lg bg-neutral-950 p-3 font-mono text-[11px] leading-relaxed text-neutral-100 ds-scroll">
                <code>
                  {PROJECTION_HEADER}
                  {"\n"}
                  {projectionLines.join("\n")}
                  {"\n"}
                  {PROJECTION_FOOTER}
                </code>
              </pre>
            </div>

            {/* Feedback */}
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Was this retrieval good?
              </p>
              {feedbackUnavailableReason && (
                <p className="mb-2 text-xs text-muted-foreground">
                  {feedbackUnavailableReason}
                </p>
              )}
              <div className="flex flex-wrap gap-2">
                <Button
                  variant={selectedFeedback === "useful" ? "default" : "outline"}
                  size="sm"
                  aria-pressed={selectedFeedback === "useful"}
                  disabled={!memoryWasProjected || savingFeedback !== null}
                  onClick={() => recordFeedback("useful")}
                >
                  <ThumbsUp className="size-3.5" /> Useful
                </Button>
                <Button
                  variant={selectedFeedback === "not_useful" ? "default" : "outline"}
                  size="sm"
                  aria-pressed={selectedFeedback === "not_useful"}
                  disabled={!memoryWasProjected || savingFeedback !== null}
                  onClick={() => recordFeedback("not_useful")}
                >
                  <ThumbsDown className="size-3.5" /> Not useful
                </Button>
                <Button
                  variant={selectedFeedback === "wrong_memory" ? "default" : "outline"}
                  size="sm"
                  aria-pressed={selectedFeedback === "wrong_memory"}
                  disabled={!memoryWasProjected || savingFeedback !== null}
                  onClick={() => recordFeedback("wrong_memory")}
                >
                  <AlertTriangle className="size-3.5" /> Wrong
                </Button>
                <Button
                  variant={selectedFeedback === "should_not_have_used" ? "default" : "outline"}
                  size="sm"
                  aria-pressed={selectedFeedback === "should_not_have_used"}
                  disabled={!memoryWasProjected || savingFeedback !== null}
                  onClick={() => recordFeedback("should_not_have_used")}
                >
                  <X className="size-3.5" /> Should not have
                </Button>
              </div>
            </div>

            {/* Cross-model parity */}
            <div className="rounded-xl border border-ink-600/30 bg-ink-600/5 p-4">
              <div className="mb-2 flex items-center gap-2">
                <Shuffle className="size-4 text-primary" strokeWidth={1.75} />
                <p className="text-sm font-medium">Cross-model parity</p>
                {distinctModels.length >= 2 && (
                  <Badge variant="ink" className="gap-1 text-[10px]">
                    <Check className="size-2.5" strokeWidth={2.5} />
                    {allConsistent ? "consistent" : "divergent"}
                  </Badge>
                )}
              </div>
              {retrievalHistory.length === 0 ? (
                <p className="text-xs text-muted-foreground">
                  No cross-model retrieval history yet for this memory.
                </p>
              ) : (
                <div className="overflow-hidden rounded-lg border border-border/60">
                  <Table>
                    <TableHeader>
                      <TableRow className="hover:bg-transparent">
                        <TableHead className="pl-3 text-[11px]">Model</TableHead>
                        <TableHead className="text-[11px]">Used</TableHead>
                        <TableHead className="pr-3 text-right text-[11px]">Time</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {[...retrievalHistory]
                        .sort((a, b) => (a.timestamp < b.timestamp ? 1 : -1))
                        .map((h, i) => (
                          <TableRow key={`${h.model}-${h.timestamp}-${i}`}>
                            <TableCell className="pl-3">
                              <Badge variant="ink" className="gap-1 font-mono text-[10px] tabular">
                                <Cpu className="size-2.5" strokeWidth={2} />
                                {h.model}
                              </Badge>
                            </TableCell>
                            <TableCell>
                              {h.used ? (
                                <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-600 dark:text-emerald-400">
                                  <Check className="size-3" strokeWidth={2.5} /> used
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                                  <X className="size-3" strokeWidth={2.5} /> not used
                                </span>
                              )}
                            </TableCell>
                            <TableCell className="pr-3 text-right font-mono text-[10px] tabular text-muted-foreground">
                              {formatDateTime(h.timestamp)}
                            </TableCell>
                          </TableRow>
                        ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </div>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}

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
    <div className={cn("space-y-1", emphasize && "rounded-lg bg-primary/10 p-2 -m-2")}>
      <dt className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="text-sm font-medium">{value}</dd>
    </div>
  );
}
