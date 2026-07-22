import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import MemoryCenterPage from "@/app/app/memory/page";
import { useMemoryStore } from "@/store/memory-store";

const mocks = vi.hoisted(() => ({
  toast: Object.assign(vi.fn(), { success: vi.fn(), error: vi.fn() }),
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

describe("memory center actions", () => {
  it("waits for explicit consent persistence before showing pause success", async () => {
    const user = userEvent.setup();
    const state = useMemoryStore.getState();
    const pending = deferred<typeof state.currentUser>();
    const setMemoryEnabled = vi.fn(() => pending.promise);
    useMemoryStore.setState({ setMemoryEnabled });
    render(<MemoryCenterPage />);

    await user.click(screen.getByRole("button", { name: "Pause" }));

    expect(setMemoryEnabled).toHaveBeenCalledWith(false);
    expect(screen.getByRole("button", { name: /Pausing/ })).toBeDisabled();
    expect(mocks.toast.success).not.toHaveBeenCalled();

    pending.resolve({ ...state.currentUser, memory_enabled: false });
    await waitFor(() => expect(mocks.toast.success).toHaveBeenCalled());
  });

  it("persists an explicitly entered memory before closing the dialog", async () => {
    const user = userEvent.setup();
    const pending = deferred<{ event_id: string; results: { id: string; action: string }[] }>();
    const addMemory = vi.fn(() => pending.promise);
    useMemoryStore.setState({ addMemory });
    render(<MemoryCenterPage />);

    await user.click(screen.getByRole("button", { name: "Tell Luna" }));
    await user.type(screen.getByLabelText("Memory to save"), "I prefer jasmine tea");
    await user.click(screen.getByRole("button", { name: "Remember this" }));

    expect(addMemory).toHaveBeenCalledWith("I prefer jasmine tea", "preference");
    expect(screen.getByRole("button", { name: /Saving/ })).toBeDisabled();
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    pending.resolve({ event_id: "evt-new", results: [{ id: "mem-new", action: "created" }] });
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(mocks.toast.success).toHaveBeenCalled();
  });

  it("downloads the Blob returned by the export service", async () => {
    const user = userEvent.setup();
    const blob = new Blob(["{}"], { type: "application/json" });
    const exportMemories = vi.fn().mockResolvedValue({ export_id: "exp-123", blob });
    const createObjectURL = vi.fn(() => "blob:memory-export");
    const revokeObjectURL = vi.fn();
    Object.defineProperty(URL, "createObjectURL", { configurable: true, value: createObjectURL });
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: revokeObjectURL });
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    useMemoryStore.setState({ exportMemories });
    render(<MemoryCenterPage />);

    await user.click(screen.getByRole("button", { name: "More" }));
    await user.click(await screen.findByRole("menuitem", { name: "Export" }));

    await waitFor(() => expect(exportMemories).toHaveBeenCalledOnce());
    expect(createObjectURL).toHaveBeenCalledWith(blob);
    expect(click).toHaveBeenCalled();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:memory-export");
    click.mockRestore();
  });
});
