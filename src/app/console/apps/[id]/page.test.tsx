import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AppDetailPage from "@/app/console/apps/[id]/page";
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
  const state = useMemoryStore.getState();
  useMemoryStore.setState({
    hydrated: true,
    backendReachable: true,
    dataMode: "live",
    app: {
      ...state.app,
      api_keys: [
        {
          ...state.app.api_keys[0],
          id: "key_masked",
          key: "mp_sandbox_abcd...wxyz",
        },
      ],
    },
  });
});

describe("App keys", () => {
  it("creates a key through the store and shows the one-time secret", async () => {
    const user = userEvent.setup();
    const state = useMemoryStore.getState();
    const created = {
      ...state.app.api_keys[0],
      id: "key_new",
      key: "mp_sandbox_new_secret",
    };
    const createApiKey = vi.fn().mockResolvedValue(created);
    useMemoryStore.setState({ createApiKey });

    render(<AppDetailPage />);
    await user.click(screen.getByRole("button", { name: /new key/i }));

    await waitFor(() =>
      expect(createApiKey).toHaveBeenCalledWith(state.app.id, {
        label: "Console key",
        environment: state.app.environment,
      }),
    );
    expect(await screen.findByText("mp_sandbox_new_secret")).toBeInTheDocument();
    expect(screen.getByText("One-time API key")).toBeInTheDocument();
  });

  it("rotates through the store and exposes only the returned replacement secret", async () => {
    const user = userEvent.setup();
    const state = useMemoryStore.getState();
    const rotated = {
      ...state.app.api_keys[0],
      id: "key_rotated",
      key: "mp_sandbox_rotated_secret",
    };
    const rotateApiKey = vi.fn().mockResolvedValue(rotated);
    useMemoryStore.setState({ rotateApiKey });

    render(<AppDetailPage />);
    await user.click(screen.getByRole("button", { name: /roll key/i }));

    await waitFor(() =>
      expect(rotateApiKey).toHaveBeenCalledWith(state.app.id, "key_masked"),
    );
    expect(await screen.findByText("mp_sandbox_rotated_secret")).toBeInTheDocument();
  });

  it("waits for clipboard completion before claiming copy success", async () => {
    const user = userEvent.setup();
    const state = useMemoryStore.getState();
    const created = {
      ...state.app.api_keys[0],
      id: "key_new",
      key: "mp_sandbox_new_secret",
    };
    useMemoryStore.setState({ createApiKey: vi.fn().mockResolvedValue(created) });
    const clipboard = deferred<void>();
    const writeText = vi.fn(() => clipboard.promise);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });

    render(<AppDetailPage />);
    await user.click(screen.getByRole("button", { name: /new key/i }));
    await screen.findByText("mp_sandbox_new_secret");
    await user.click(screen.getByRole("button", { name: /copy new api key/i }));

    expect(toast.success).not.toHaveBeenCalledWith("API key copied");
    clipboard.resolve();
    await waitFor(() => expect(toast.success).toHaveBeenCalledWith("API key copied"));
  });

  it("does not report success when key creation fails", async () => {
    const user = userEvent.setup();
    useMemoryStore.setState({
      createApiKey: vi.fn().mockRejectedValue(new Error("key service failed")),
    });

    render(<AppDetailPage />);
    await user.click(screen.getByRole("button", { name: /new key/i }));

    await waitFor(() => expect(toast.error).toHaveBeenCalled());
    expect(toast.success).not.toHaveBeenCalled();
    expect(screen.queryByText("One-time API key")).not.toBeInTheDocument();
  });
});

describe("Integration status", () => {
  it("reflects live store progress instead of declaring every step ready", () => {
    useMemoryStore.setState({
      quickstart: {
        apiKeyCreated: true,
        testUserCreated: false,
        firstEventSent: false,
        firstRetrieveDone: false,
      },
    });

    render(<AppDetailPage />);

    expect(screen.getByTestId("integration-api-key")).toHaveTextContent("Ready");
    expect(screen.getByTestId("integration-test-user")).toHaveTextContent("Not tested");
    expect(screen.getByTestId("integration-first-event")).toHaveTextContent("Not tested");
    expect(screen.getByTestId("integration-retrieve")).toHaveTextContent("Not tested");
  });
});
