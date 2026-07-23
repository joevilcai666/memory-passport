import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import MigrationPreviewPage from "@/app/app/migrate/page";
import { useMemoryStore } from "@/store/memory-store";

const mocks = vi.hoisted(() => ({
  push: vi.fn(),
  replace: vi.fn(),
  toast: Object.assign(vi.fn(), { success: vi.fn(), error: vi.fn() }),
}));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mocks.push, replace: mocks.replace }),
}));
vi.mock("sonner", () => ({ toast: mocks.toast }));

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
  useMemoryStore.setState({ hydrated: true, backendReachable: true, dataMode: "live" });
});

describe("migration preview", () => {
  it("selects recommended memories without collapsing the bucket", async () => {
    const user = userEvent.setup();
    render(<MigrationPreviewPage />);

    const firstRecommended = useMemoryStore
      .getState()
      .memories.find(
        (memory) => memory.portability.layer === "portable" && memory.confidence >= 0.7,
      );
    expect(firstRecommended).toBeDefined();
    expect(screen.getByText(firstRecommended!.content)).toBeVisible();

    await user.click(screen.getByRole("button", { name: "Select all" }));

    expect(screen.getByRole("button", { name: "Deselect all" })).toBeInTheDocument();
    expect(screen.getByText(firstRecommended!.content)).toBeVisible();
  });

  it("counts every unselected portable and device-local memory as skipped", () => {
    const state = useMemoryStore.getState();
    const base = state.memories[0];
    const relationshipId = state.migration.source_relationship_id;
    useMemoryStore.setState({
      memories: [
        {
          ...base,
          id: "recommended",
          content: "Recommended memory",
          relationship_id: relationshipId,
          confidence: 0.9,
          portability: { ...base.portability, layer: "portable" },
        },
        {
          ...base,
          id: "review",
          content: "Review memory",
          relationship_id: relationshipId,
          confidence: 0.4,
          portability: { ...base.portability, layer: "portable" },
        },
        {
          ...base,
          id: "local",
          content: "Local memory",
          relationship_id: relationshipId,
          portability: { ...base.portability, layer: "device_local" },
        },
      ],
      migration: { ...state.migration, selected_memory_ids: [] },
    });

    render(<MigrationPreviewPage />);

    expect(screen.getByText(/Skipping 3/)).toBeInTheDocument();
  });

  it("waits for migration completion before reporting success and navigating", async () => {
    const user = userEvent.setup();
    const state = useMemoryStore.getState();
    const selected = state.memories[0].id;
    const completed = {
      ...state.migration,
      status: "completed" as const,
      selected_memory_ids: [selected],
      completed_at: new Date().toISOString(),
    };
    const pending = deferred<typeof completed>();
    const executeMigration = vi.fn(() => pending.promise);
    useMemoryStore.setState({
      migration: { ...state.migration, selected_memory_ids: [selected] },
      executeMigration,
    });
    render(<MigrationPreviewPage />);

    await user.click(screen.getByRole("button", { name: /Move 1 memory/ }));

    expect(executeMigration).toHaveBeenCalledOnce();
    expect(screen.getByRole("button", { name: /Moving/ })).toBeDisabled();
    expect(mocks.toast.success).not.toHaveBeenCalled();
    expect(mocks.push).not.toHaveBeenCalled();

    pending.resolve(completed);
    await waitFor(() => expect(mocks.push).toHaveBeenCalledWith("/app/migrate/complete"));
    expect(mocks.toast.success).toHaveBeenCalled();
  });

  it("reports migration failure without navigating", async () => {
    const user = userEvent.setup();
    const state = useMemoryStore.getState();
    useMemoryStore.setState({
      migration: { ...state.migration, selected_memory_ids: [state.memories[0].id] },
      executeMigration: vi.fn().mockRejectedValue(new Error("migration failed")),
    });
    render(<MigrationPreviewPage />);

    await user.click(screen.getByRole("button", { name: /Move 1 memory/ }));

    await waitFor(() => expect(mocks.toast.error).toHaveBeenCalled());
    expect(mocks.toast.success).not.toHaveBeenCalled();
    expect(mocks.push).not.toHaveBeenCalled();
  });
});
