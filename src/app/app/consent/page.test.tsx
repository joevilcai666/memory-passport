import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ConsentPage from "@/app/app/consent/page";
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
});

describe("memory consent", () => {
  it("sets explicit consent and navigates only after the backend responds", async () => {
    const user = userEvent.setup();
    const pending = deferred<ReturnType<typeof useMemoryStore.getState>["currentUser"]>();
    const setMemoryEnabled = vi.fn(() => pending.promise);
    useMemoryStore.setState({ setMemoryEnabled });

    render(<ConsentPage />);
    await user.click(screen.getByRole("button", { name: "Turn on" }));

    expect(setMemoryEnabled).toHaveBeenCalledWith(true);
    expect(screen.getByRole("button", { name: /turning on/i })).toBeDisabled();
    expect(mocks.push).not.toHaveBeenCalled();
    expect(mocks.toast.success).not.toHaveBeenCalled();

    pending.resolve({
      ...useMemoryStore.getState().currentUser,
      memory_enabled: true,
    });
    await waitFor(() => expect(mocks.push).toHaveBeenCalledWith("/app/memory"));
    expect(mocks.toast.success).toHaveBeenCalledWith(
      "Memory is on",
      expect.any(Object),
    );
  });

  it("shows an error and stays put when consent fails", async () => {
    const user = userEvent.setup();
    useMemoryStore.setState({
      setMemoryEnabled: vi.fn().mockRejectedValue(new Error("consent failed")),
    });

    render(<ConsentPage />);
    await user.click(screen.getByRole("button", { name: "Turn on" }));

    await waitFor(() => expect(mocks.toast.error).toHaveBeenCalled());
    expect(mocks.push).not.toHaveBeenCalled();
    expect(mocks.toast.success).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Turn on" })).toBeEnabled();
  });
});
