import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import SettingsPage from "@/app/console/settings/page";
import { useMemoryStore } from "@/store/memory-store";

const toast = vi.hoisted(() =>
  Object.assign(vi.fn(), { success: vi.fn(), error: vi.fn() }),
);
vi.mock("sonner", () => ({ toast }));

beforeEach(() => {
  vi.clearAllMocks();
  useMemoryStore.setState(useMemoryStore.getInitialState(), true);
  useMemoryStore.setState({
    hydrated: true,
    backendReachable: true,
    dataMode: "live",
    pendingInvites: [],
  });
});

describe("Team invitations", () => {
  it("issues a real invite, copies its real URL, and renders it pending", async () => {
    const user = userEvent.setup();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });
    const result = {
      invite: {
        id: "tmi_real",
        email: "new@example.com",
        role: "Support" as const,
        created_by: "owner@example.com",
        created_at: "2026-07-22T00:00:00Z",
        expires_at: "2026-07-29T00:00:00Z",
        accepted_at: null,
      },
      token: "real-invite-token",
    };
    const inviteTeamMember = vi.fn().mockResolvedValue(result);
    useMemoryStore.setState({ inviteTeamMember });

    render(<SettingsPage />);
    await user.click(screen.getByRole("button", { name: /invite member/i }));
    await user.type(screen.getByPlaceholderText("teammate@example.com"), "new@example.com");
    await user.click(screen.getByRole("button", { name: /create invite/i }));

    await waitFor(() =>
      expect(inviteTeamMember).toHaveBeenCalledWith({
        email: "new@example.com",
        role: "Support",
      }),
    );
    const expectedUrl = `${window.location.origin}/invite/real-invite-token`;
    expect(writeText).toHaveBeenCalledWith(expectedUrl);
    expect(await screen.findByText("Pending invitation")).toBeInTheDocument();
    expect(screen.getByText(/new@example\.com/)).toBeInTheDocument();
    expect(screen.getByText(expectedUrl)).toBeInTheDocument();
  });

  it("does not claim success when the invite request fails", async () => {
    const user = userEvent.setup();
    useMemoryStore.setState({
      inviteTeamMember: vi.fn().mockRejectedValue(new Error("invite failed")),
    });

    render(<SettingsPage />);
    await user.click(screen.getByRole("button", { name: /invite member/i }));
    await user.type(screen.getByPlaceholderText("teammate@example.com"), "new@example.com");
    await user.click(screen.getByRole("button", { name: /create invite/i }));

    await waitFor(() => expect(toast.error).toHaveBeenCalled());
    expect(toast.success).not.toHaveBeenCalled();
    expect(screen.queryByText("Pending invitation")).not.toBeInTheDocument();
  });
});
