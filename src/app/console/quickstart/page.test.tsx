import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import QuickstartPage from "@/app/console/quickstart/page";
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
  useMemoryStore.setState({
    hydrated: true,
    backendReachable: true,
    dataMode: "live",
    quickstart: {
      apiKeyCreated: true,
      testUserCreated: true,
      firstEventSent: false,
      firstRetrieveDone: false,
    },
  });
});

describe("Quickstart live actions", () => {
  it("awaits the real ingest response before reporting success", async () => {
    const user = userEvent.setup();
    const pending = deferred<{ event_id: string; results: [] } | null>();
    useMemoryStore.setState({ runTestEvent: vi.fn(() => pending.promise) });

    render(<QuickstartPage />);
    await user.click(screen.getByRole("button", { name: /run test event/i }));

    expect(screen.getByRole("button", { name: /sending event/i })).toBeDisabled();
    expect(toast.success).not.toHaveBeenCalled();

    pending.resolve({ event_id: "evt_real", results: [] });
    await waitFor(() =>
      expect(toast.success).toHaveBeenCalledWith(
        "Event received",
        expect.objectContaining({ description: "evt_real" }),
      ),
    );
  });

  it("shows a failure and re-enables the test action", async () => {
    const user = userEvent.setup();
    useMemoryStore.setState({
      runTestEvent: vi.fn().mockRejectedValue(new Error("ingest failed")),
    });

    render(<QuickstartPage />);
    await user.click(screen.getByRole("button", { name: /run test event/i }));

    await waitFor(() => expect(toast.error).toHaveBeenCalled());
    expect(screen.getByRole("button", { name: /run test event/i })).toBeEnabled();
    expect(toast.success).not.toHaveBeenCalled();
  });

  it("contains no links to the removed debugger route", () => {
    useMemoryStore.setState({
      quickstart: {
        apiKeyCreated: true,
        testUserCreated: true,
        firstEventSent: true,
        firstRetrieveDone: true,
      },
    });

    const { container } = render(<QuickstartPage />);
    expect(container.querySelector('a[href="/console/memory/debugger"]')).toBeNull();
    expect(container.querySelector('a[href="/console/memory/users"]')).not.toBeNull();
  });
});
