import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DeleteAllPage from "@/app/app/memory/delete/page";
import { useMemoryStore } from "@/store/memory-store";

const mocks = vi.hoisted(() => ({
  push: vi.fn(),
  toast: Object.assign(vi.fn(), { success: vi.fn(), error: vi.fn() }),
}));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: mocks.push }) }));
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

describe("delete all memories", () => {
  it("waits for the atomic backend deletion before navigating", async () => {
    const user = userEvent.setup();
    const state = useMemoryStore.getState();
    const result = {
      user_id: state.currentUser.id,
      tombstoned_memories: 3,
      hms_bank_deleted: true,
      passport_status: "deleted" as const,
    };
    const pending = deferred<typeof result>();
    const deleteAllMemories = vi.fn(() => pending.promise);
    useMemoryStore.setState({ deleteAllMemories });
    render(<DeleteAllPage />);

    await user.type(screen.getByLabelText(/Type DELETE/), "DELETE");
    await user.click(screen.getByRole("button", { name: "Delete forever" }));

    expect(deleteAllMemories).toHaveBeenCalledOnce();
    expect(screen.getByRole("button", { name: /Deleting/ })).toBeDisabled();
    expect(mocks.push).not.toHaveBeenCalled();
    pending.resolve(result);

    await waitFor(() => expect(mocks.push).toHaveBeenCalledWith("/app/memory"));
    expect(mocks.toast.success).toHaveBeenCalledWith(
      "All memories deleted",
      expect.objectContaining({ description: expect.stringContaining("3") }),
    );
  });

  it("reports deletion failure without navigating", async () => {
    const user = userEvent.setup();
    useMemoryStore.setState({
      deleteAllMemories: vi.fn().mockRejectedValue(new Error("delete failed")),
    });
    render(<DeleteAllPage />);

    await user.type(screen.getByLabelText(/Type DELETE/), "DELETE");
    await user.click(screen.getByRole("button", { name: "Delete forever" }));

    await waitFor(() => expect(mocks.toast.error).toHaveBeenCalled());
    expect(mocks.push).not.toHaveBeenCalled();
    expect(mocks.toast.success).not.toHaveBeenCalled();
  });
});
