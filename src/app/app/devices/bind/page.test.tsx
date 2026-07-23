import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import BindDevicePage from "@/app/app/devices/bind/page";
import type { Device } from "@/lib/types";
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

describe("device registration and binding", () => {
  it("uses the registered device and one-time pairing code for a real bind", async () => {
    const user = userEvent.setup();
    const state = useMemoryStore.getState();
    const registered = {
      device: {
        ...state.devices[0],
        id: "dev_registered_real",
        model: "Luna Robot",
        generation: "v2",
        status: "registered" as const,
        bound_user_id: null,
      },
      pairing_code: "PAIR1234",
    };
    const registerPending = deferred<typeof registered>();
    const bindPending = deferred<Device>();
    const registerDevice = vi.fn(() => registerPending.promise);
    const bindDevice = vi.fn(() => bindPending.promise);
    useMemoryStore.setState({ registerDevice, bindDevice });

    render(<BindDevicePage />);
    await user.click(screen.getByRole("button", { name: "Register test device" }));
    expect(registerDevice).toHaveBeenCalledWith(expect.objectContaining({
      model: "Luna Robot",
      generation: "v2",
    }));
    expect(screen.getByRole("button", { name: /registering/i })).toBeDisabled();

    registerPending.resolve(registered);
    expect(await screen.findByText("PAIR1234")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Bind to my Passport" }));

    expect(bindDevice).toHaveBeenCalledWith({
      device_id: "dev_registered_real",
      user_id: state.currentUser.id,
      pairing_code: "PAIR1234",
    });
    expect(mocks.push).not.toHaveBeenCalled();
    bindPending.resolve({ ...registered.device, status: "bound", bound_user_id: state.currentUser.id });

    await waitFor(() => expect(mocks.push).toHaveBeenCalledWith("/app/devices"));
    expect(mocks.toast.success).toHaveBeenCalled();
  });

  it("binds an existing registered device with a manually entered code", async () => {
    const user = userEvent.setup();
    const state = useMemoryStore.getState();
    const target = {
      ...state.devices[0],
      id: "dev_waiting",
      status: "registered" as const,
      bound_user_id: null,
    };
    const bindDevice = vi.fn().mockResolvedValue({
      ...target,
      status: "bound",
      bound_user_id: state.currentUser.id,
    });
    useMemoryStore.setState({ devices: [target], bindDevice });

    render(<BindDevicePage />);
    await user.type(screen.getByLabelText("Pairing code"), "manual12");
    await user.click(screen.getByRole("button", { name: "Bind to my Passport" }));

    await waitFor(() =>
      expect(bindDevice).toHaveBeenCalledWith({
        device_id: "dev_waiting",
        user_id: state.currentUser.id,
        pairing_code: "MANUAL12",
      }),
    );
  });

  it("reports bind failure without navigating", async () => {
    const user = userEvent.setup();
    const state = useMemoryStore.getState();
    const target = { ...state.devices[0], status: "registered" as const, bound_user_id: null };
    useMemoryStore.setState({
      devices: [target],
      bindDevice: vi.fn().mockRejectedValue(new Error("invalid pairing code")),
    });

    render(<BindDevicePage />);
    await user.type(screen.getByLabelText("Pairing code"), "wrong123");
    await user.click(screen.getByRole("button", { name: "Bind to my Passport" }));

    await waitFor(() => expect(mocks.toast.error).toHaveBeenCalled());
    expect(mocks.push).not.toHaveBeenCalled();
    expect(mocks.toast.success).not.toHaveBeenCalled();
  });
});
