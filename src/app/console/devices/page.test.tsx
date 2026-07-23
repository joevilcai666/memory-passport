import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import DevicesConsolePage from "@/app/console/devices/page";
import { useMemoryStore } from "@/store/memory-store";

beforeEach(() => {
  useMemoryStore.setState(useMemoryStore.getInitialState(), true);
});

describe("Device and migration truthfulness", () => {
  it("renders only store-derived migration and device metrics", () => {
    const state = useMemoryStore.getState();
    useMemoryStore.setState({
      devices: [
        { ...state.devices[0], id: "dev_bound", status: "bound" },
        { ...state.devices[1], id: "dev_wiped", status: "wiped" },
      ],
      migration: {
        ...state.migration,
        id: "mig_current_real",
        status: "preview",
        selected_memory_ids: ["mem_1", "mem_2"],
      },
    });

    render(<DevicesConsolePage />);

    expect(screen.getAllByText("Current migration").length).toBeGreaterThan(0);
    expect(screen.getByText("2 selected")).toBeInTheDocument();
    expect(screen.getByText("1 wiped device")).toBeInTheDocument();
    expect(screen.queryByText("Alex Rivera")).not.toBeInTheDocument();
    expect(screen.queryByText("Sam Okafor")).not.toBeInTheDocument();
    expect(screen.queryByText("98.1%")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Migration actions" })).not.toBeInTheDocument();
  });
});
