import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import OverviewPage from "@/app/console/page";
import { useMemoryStore } from "@/store/memory-store";

vi.mock("@/components/console/ActivityChart", () => ({
  ActivityChart: () => <div>Activity chart</div>,
}));

beforeEach(() => {
  useMemoryStore.setState(useMemoryStore.getInitialState(), true);
});

describe("System status", () => {
  it("labels offline demo data honestly", () => {
    useMemoryStore.setState({
      hydrated: true,
      backendReachable: false,
      dataMode: "offline-demo",
    });

    render(<OverviewPage />);

    expect(screen.getByText("Offline demo")).toBeInTheDocument();
    expect(screen.queryByText("Operational")).not.toBeInTheDocument();
    expect(screen.getAllByText("Unavailable").length).toBeGreaterThan(0);
  });

  it("derives live checks from quickstart and migration state", () => {
    useMemoryStore.setState({
      hydrated: true,
      backendReachable: true,
      dataMode: "live",
      quickstart: {
        apiKeyCreated: true,
        testUserCreated: true,
        firstEventSent: true,
        firstRetrieveDone: false,
      },
      migration: {
        ...useMemoryStore.getState().migration,
        status: "preview",
      },
    });

    render(<OverviewPage />);

    expect(screen.getByText("Backend reachable")).toBeInTheDocument();
    expect(screen.getByTestId("system-ingest")).toHaveTextContent("Tested");
    expect(screen.getByTestId("system-retrieve")).toHaveTextContent("Not tested");
    expect(screen.getByTestId("system-migration")).toHaveTextContent("Preview");
    expect(screen.queryByText(/p99/i)).not.toBeInTheDocument();
  });
});
