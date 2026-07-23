import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import MemoryDetailPage from "@/app/app/memory/[id]/page";
import { useMemoryStore } from "@/store/memory-store";

const mocks = vi.hoisted(() => ({
  push: vi.fn(),
  replace: vi.fn(),
  memoryId: "",
  toast: Object.assign(vi.fn(), { success: vi.fn(), error: vi.fn() }),
}));
vi.mock("next/navigation", () => ({
  useParams: () => ({ id: mocks.memoryId }),
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
  mocks.memoryId = useMemoryStore.getState().memories[0].id;
});

describe("memory detail mutations", () => {
  it("keeps the edit dialog open and reports a failed update", async () => {
    const user = userEvent.setup();
    useMemoryStore.setState({ editMemory: vi.fn().mockRejectedValue(new Error("update failed")) });
    render(<MemoryDetailPage />);

    await user.click(screen.getByRole("button", { name: "Edit" }));
    const editor = screen.getByLabelText("Memory content");
    await user.clear(editor);
    await user.type(editor, "Updated memory");
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(mocks.toast.error).toHaveBeenCalled());
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(mocks.toast.success).not.toHaveBeenCalled();
  });

  it("waits for deletion before closing and navigating", async () => {
    const user = userEvent.setup();
    const state = useMemoryStore.getState();
    const memory = state.memories[0];
    const pending = deferred<typeof memory>();
    const deleteMemory = vi.fn(() => pending.promise);
    useMemoryStore.setState({ deleteMemory });
    render(<MemoryDetailPage />);

    await user.click(screen.getByRole("button", { name: "Delete" }));
    await user.click(screen.getByRole("button", { name: "Delete forever" }));

    expect(deleteMemory).toHaveBeenCalledWith(memory.id);
    expect(mocks.push).not.toHaveBeenCalled();
    pending.resolve({ ...memory, status: "deleted" });

    await waitFor(() => expect(mocks.push).toHaveBeenCalledWith("/app/memory"));
    expect(mocks.toast.success).toHaveBeenCalled();
  });

  it("reports a failed wrong-memory flag without claiming success", async () => {
    const user = userEvent.setup();
    useMemoryStore.setState({
      setMemoryStatus: vi.fn().mockRejectedValue(new Error("flag failed")),
    });
    render(<MemoryDetailPage />);

    await user.click(screen.getByRole("button", { name: "Report" }));

    await waitFor(() => expect(mocks.toast.error).toHaveBeenCalled());
    expect(mocks.toast.success).not.toHaveBeenCalled();
  });
});
