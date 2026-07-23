import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import InviteAcceptancePage from "@/app/invite/[token]/page";

const apiMock = vi.hoisted(() => ({
  previewTeamInvite: vi.fn(),
  acceptTeamInvite: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({ token: "real-invite-token" }),
}));

vi.mock("@/lib/api-client", () => ({ api: apiMock }));

beforeEach(() => {
  vi.clearAllMocks();
  apiMock.previewTeamInvite.mockResolvedValue({
    tenant_name: "Luna Inc.",
    email: "new@example.com",
    role: "Support",
    expires_at: "2026-07-29T00:00:00Z",
  });
});

describe("team invite acceptance", () => {
  it("previews and accepts the issued token through public backend endpoints", async () => {
    const user = userEvent.setup();
    apiMock.acceptTeamInvite.mockResolvedValue({
      id: "tm_new",
      name: "New Teammate",
      email: "new@example.com",
      role: "Support",
      avatar_color: "#334155",
      last_active: "2026-07-22T00:00:00Z",
    });

    render(<InviteAcceptancePage />);

    expect(await screen.findByText("Join Luna Inc.")).toBeInTheDocument();
    expect(apiMock.previewTeamInvite).toHaveBeenCalledWith("real-invite-token");
    await user.type(screen.getByLabelText("Your name"), "New Teammate");
    await user.click(screen.getByRole("button", { name: "Accept invitation" }));

    await waitFor(() =>
      expect(apiMock.acceptTeamInvite).toHaveBeenCalledWith(
        "real-invite-token",
        { name: "New Teammate" },
      ),
    );
    expect(await screen.findByText("Invitation accepted")).toBeInTheDocument();
  });

  it("renders an honest error for an expired or invalid token", async () => {
    apiMock.previewTeamInvite.mockRejectedValue(new Error("Invitation expired"));

    render(<InviteAcceptancePage />);

    expect(await screen.findByText("Invitation unavailable")).toBeInTheDocument();
    expect(screen.getByText("Invitation expired")).toBeInTheDocument();
  });
});
