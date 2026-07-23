import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import MigrationCompletePage from "@/app/app/migrate/complete/page";
import { useMemoryStore } from "@/store/memory-store";

const mocks = vi.hoisted(() => ({ replace: vi.fn() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mocks.replace }),
}));

beforeEach(() => {
  vi.clearAllMocks();
  useMemoryStore.setState(useMemoryStore.getInitialState(), true);
});

describe("migration completion summary", () => {
  it("derives moved, skipped, and failed counts from the returned migration", () => {
    const state = useMemoryStore.getState();
    useMemoryStore.setState({
      migration: {
        ...state.migration,
        status: "completed_with_warnings",
        selected_memory_ids: ["moved-1", "failed-1", "moved-2"],
        failed_memory_ids: ["failed-1"],
        skipped_memory_ids: ["skipped-1", "skipped-2"],
        completed_at: new Date().toISOString(),
      },
    });

    render(<MigrationCompletePage />);

    expect(within(screen.getByText("Moved").parentElement!).getByText("2")).toBeInTheDocument();
    expect(within(screen.getByText("Skipped").parentElement!).getByText("2")).toBeInTheDocument();
    expect(within(screen.getByText("Failed").parentElement!).getByText("1")).toBeInTheDocument();
    expect(mocks.replace).not.toHaveBeenCalled();
  });

  it("redirects incomplete migrations back to the preview", () => {
    render(<MigrationCompletePage />);
    expect(mocks.replace).toHaveBeenCalledWith("/app/migrate");
  });
});
