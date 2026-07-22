import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { MemoryTraceSheet } from "@/components/memory/MemoryTraceSheet";
import { useMemoryStore } from "@/store/memory-store";

const toast = vi.hoisted(() =>
  Object.assign(vi.fn(), { success: vi.fn(), error: vi.fn() }),
);
vi.mock("sonner", () => ({ toast }));

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((res) => {
    resolve = res;
  });
  return { promise, resolve };
}

beforeEach(() => {
  vi.clearAllMocks();
  useMemoryStore.setState(useMemoryStore.getInitialState(), true);
  const memory = useMemoryStore.getState().memories[0];
  useMemoryStore.setState({
    hydrated: true,
    backendReachable: true,
    dataMode: "live",
    lastTraceId: "trc_real",
    lastTrace: {
      id: "trc_real",
      query: "How should I respond?",
      caller: { model: "quickstart-test" },
      hms_results: { results: [] },
      projected: { results: [memory] },
      retrieval_events: { events: {} },
      feedback: null,
      created_at: "2026-07-22T00:00:00Z",
    },
  });
});

describe("retrieval feedback", () => {
  it("persists feedback before marking the category selected", async () => {
    const user = userEvent.setup();
    const memory = useMemoryStore.getState().memories[0];
    const pending = deferred<Awaited<ReturnType<ReturnType<typeof useMemoryStore.getState>["recordTraceFeedback"]>>>();
    const recordTraceFeedback = vi.fn(() => pending.promise);
    useMemoryStore.setState({ recordTraceFeedback });

    render(
      <MemoryTraceSheet
        memoryId={memory.id}
        open
        onOpenChange={vi.fn()}
      />,
    );
    const useful = await screen.findByRole("button", { name: "Useful" });
    await user.click(useful);

    expect(recordTraceFeedback).toHaveBeenCalledWith("trc_real", {
      memory_id: memory.id,
      category: "useful",
    });
    expect(useful).toHaveAttribute("aria-pressed", "false");
    expect(toast.success).not.toHaveBeenCalled();

    pending.resolve({
      id: "trc_real",
      query: "test",
      caller: {},
      hms_results: {},
      projected: { results: [] },
      retrieval_events: {},
      feedback: {
        memory_id: memory.id,
        category: "useful",
        actor: "owner@example.com",
        recorded_at: "2026-07-22T00:00:00Z",
      },
      created_at: "2026-07-22T00:00:00Z",
    });

    await waitFor(() => expect(useful).toHaveAttribute("aria-pressed", "true"));
    expect(toast.success).toHaveBeenCalledWith("Feedback recorded");
  });

  it("disables feedback when no real retrieval trace exists", async () => {
    const memory = useMemoryStore.getState().memories[0];
    useMemoryStore.setState({ lastTraceId: null, lastTrace: null });

    render(
      <MemoryTraceSheet
        memoryId={memory.id}
        open
        onOpenChange={vi.fn()}
      />,
    );

    expect(await screen.findByText(/run a retrieve test first/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Useful" })).toBeDisabled();
  });

  it("rejects feedback selection for a memory outside the loaded trace", async () => {
    const memory = useMemoryStore.getState().memories[0];
    useMemoryStore.setState({
      lastTrace: {
        ...useMemoryStore.getState().lastTrace!,
        projected: { results: [] },
      },
    });

    render(
      <MemoryTraceSheet
        memoryId={memory.id}
        open
        onOpenChange={vi.fn()}
      />,
    );

    expect(await screen.findByText(/was not projected by the loaded trace/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Useful" })).toBeDisabled();
  });
});
