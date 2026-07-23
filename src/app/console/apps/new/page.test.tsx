import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import NewAppPage from "@/app/console/apps/new/page";
import { useMemoryStore } from "@/store/memory-store";

const mocks = vi.hoisted(() => ({
  push: vi.fn(),
  back: vi.fn(),
  toast: Object.assign(vi.fn(), {
    success: vi.fn(),
    error: vi.fn(),
  }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mocks.push, back: mocks.back }),
}));

vi.mock("sonner", () => ({ toast: mocks.toast }));

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

beforeEach(() => {
  vi.clearAllMocks();
  useMemoryStore.setState(useMemoryStore.getInitialState(), true);
});

describe("Create app", () => {
  it("waits for the backend and shows the one-time key before navigation", async () => {
    const user = userEvent.setup();
    const pending = deferred<Awaited<ReturnType<ReturnType<typeof useMemoryStore.getState>["createApp"]>>>();
    const initial = useMemoryStore.getState();
    const createApp = vi.fn(() => pending.promise);
    useMemoryStore.setState({ createApp });

    render(<NewAppPage />);
    await user.type(screen.getByPlaceholderText("e.g. Luna"), "Atlas");
    await user.click(screen.getByRole("button", { name: /create app/i }));

    expect(createApp).toHaveBeenCalledWith({
      name: "Atlas",
      product_type: "hybrid",
      environment: "sandbox",
      data_region: "us-east-1",
      show_powered_by: true,
    });
    expect(mocks.push).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: /creating/i })).toBeDisabled();

    pending.resolve({
      app: { ...initial.app, id: "app_atlas", name: "Atlas" },
      api_key: {
        ...initial.app.api_keys[0],
        id: "key_once",
        key: "mp_sandbox_one_time_secret",
      },
    });

    expect(await screen.findByText("Save this API key now")).toBeInTheDocument();
    expect(screen.getByText("mp_sandbox_one_time_secret")).toBeInTheDocument();
    expect(mocks.push).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: /continue to quickstart/i }));
    expect(mocks.push).toHaveBeenCalledWith("/console/quickstart");
  });

  it("reports backend failure and never navigates", async () => {
    const user = userEvent.setup();
    useMemoryStore.setState({
      createApp: vi.fn().mockRejectedValue(new Error("create unavailable")),
    });

    render(<NewAppPage />);
    await user.type(screen.getByPlaceholderText("e.g. Luna"), "Atlas");
    await user.click(screen.getByRole("button", { name: /create app/i }));

    await waitFor(() =>
      expect(mocks.toast.error).toHaveBeenCalledWith(
        "App creation failed",
        expect.objectContaining({ description: "create unavailable" }),
      ),
    );
    expect(mocks.push).not.toHaveBeenCalled();
    expect(screen.queryByText("Save this API key now")).not.toBeInTheDocument();
  });
});
