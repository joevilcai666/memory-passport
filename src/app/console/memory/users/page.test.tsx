import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import UsersPage from "@/app/console/memory/users/page";
import { useMemoryStore } from "@/store/memory-store";

const mocks = vi.hoisted(() => ({
  toast: Object.assign(vi.fn(), { success: vi.fn(), error: vi.fn() }),
}));
vi.mock("sonner", () => ({ toast: mocks.toast }));
vi.mock("@/components/memory/MemoryTraceSheet", () => ({
  MemoryTraceSheet: () => null,
}));

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

describe("console memory mutations", () => {
  it("edits a memory through the backend before closing the dialog", async () => {
    const user = userEvent.setup();
    const memory = useMemoryStore.getState().memories[0];
    const pending = deferred<typeof memory>();
    const editMemory = vi.fn(() => pending.promise);
    useMemoryStore.setState({ editMemory });
    render(<UsersPage />);

    await user.click(screen.getAllByRole("button", { name: "Memory actions" })[0]);
    await user.click(await screen.findByRole("menuitem", { name: "Edit" }));
    const editor = screen.getByLabelText("Memory content");
    await user.clear(editor);
    await user.type(editor, "Updated from console");
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    expect(editMemory).toHaveBeenCalledWith(memory.id, "Updated from console");
    expect(screen.getByRole("button", { name: /Saving/ })).toBeDisabled();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(mocks.toast.success).not.toHaveBeenCalled();

    pending.resolve({ ...memory, content: "Updated from console", version: memory.version + 1 });
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(mocks.toast.success).toHaveBeenCalled();
  });

  it("reports an archive failure without claiming success", async () => {
    const user = userEvent.setup();
    const setMemoryStatus = vi.fn().mockRejectedValue(new Error("archive failed"));
    useMemoryStore.setState({ setMemoryStatus });
    render(<UsersPage />);

    await user.click(screen.getAllByRole("button", { name: "Memory actions" })[0]);
    await user.click(await screen.findByRole("menuitem", { name: "Archive" }));

    await waitFor(() => expect(mocks.toast.error).toHaveBeenCalled());
    expect(setMemoryStatus).toHaveBeenCalledWith(useMemoryStore.getState().memories[0].id, "archived");
    expect(mocks.toast.success).not.toHaveBeenCalled();
  });

  it("waits for deletion before reporting success", async () => {
    const user = userEvent.setup();
    const memory = useMemoryStore.getState().memories[0];
    const pending = deferred<typeof memory>();
    const deleteMemory = vi.fn(() => pending.promise);
    useMemoryStore.setState({ deleteMemory });
    render(<UsersPage />);

    await user.click(screen.getAllByRole("button", { name: "Memory actions" })[0]);
    await user.click(await screen.findByRole("menuitem", { name: /Delete/ }));

    expect(deleteMemory).toHaveBeenCalledWith(memory.id);
    expect(mocks.toast.success).not.toHaveBeenCalled();
    pending.resolve({ ...memory, status: "deleted" });

    await waitFor(() => expect(mocks.toast.success).toHaveBeenCalled());
  });
});
