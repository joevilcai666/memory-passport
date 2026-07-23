import { afterEach, describe, expect, it, vi } from "vitest";
import { seedMemories } from "@/lib/mock-data";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.resetModules();
});

describe("authoritative memory edits", () => {
  it("renders the server-returned version only after persistence succeeds", async () => {
    const original = structuredClone(seedMemories[0]);
    const authoritative = {
      ...original,
      id: "mem_server_version_2",
      content: "The persisted server content",
      version: original.version + 1,
      supersedes: original.id,
    };
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => Response.json(authoritative)),
    );

    const { useMemoryStore } = await import("@/store/memory-store");
    const auditBefore = structuredClone(useMemoryStore.getState().auditLogs);
    useMemoryStore.setState({
      memories: [original],
      auditLogs: auditBefore,
      backendReachable: true,
      dataMode: "live",
    });

    const result = await useMemoryStore
      .getState()
      .editMemory(original.id, authoritative.content);

    expect(result).toEqual(authoritative);
    expect(useMemoryStore.getState().memories).toEqual([authoritative]);
    expect(useMemoryStore.getState().auditLogs).toEqual(auditBefore);
  });

  it("keeps the last authoritative memory and exposes a 5xx edit error", async () => {
    const original = structuredClone(seedMemories[0]);
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        Response.json(
          { detail: { code: "hms_mutation_failed" } },
          { status: 502, statusText: "Bad Gateway" },
        ),
      ),
    );

    const { useMemoryStore } = await import("@/store/memory-store");
    useMemoryStore.setState({
      memories: [original],
      backendReachable: true,
      dataMode: "live",
    });

    await expect(
      useMemoryStore
        .getState()
        .editMemory(original.id, "This must never appear as saved"),
    ).rejects.toThrow();
    expect(useMemoryStore.getState().memories).toEqual([original]);
  });

  it("does not mutate seeded data when the backend is unavailable", async () => {
    const original = structuredClone(seedMemories[0]);
    const browserFetch = vi.fn();
    vi.stubGlobal("fetch", browserFetch);

    const { useMemoryStore } = await import("@/store/memory-store");
    useMemoryStore.setState({
      memories: [original],
      backendReachable: false,
      dataMode: "offline-demo",
    });

    await expect(
      useMemoryStore.getState().editMemory(original.id, "An offline fake edit"),
    ).rejects.toThrow(/read-only/i);
    expect(useMemoryStore.getState().memories).toEqual([original]);
    expect(browserFetch).not.toHaveBeenCalled();
  });

  it("keeps the last authoritative memory when the credential is rejected", async () => {
    const original = structuredClone(seedMemories[0]);
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        Response.json(
          { detail: { code: "invalid_api_key" } },
          { status: 401, statusText: "Unauthorized" },
        ),
      ),
    );

    const { useMemoryStore } = await import("@/store/memory-store");
    useMemoryStore.setState({
      memories: [original],
      backendReachable: true,
      dataMode: "live",
    });

    await expect(
      useMemoryStore
        .getState()
        .editMemory(original.id, "An unauthorized fake edit"),
    ).rejects.toThrow();
    expect(useMemoryStore.getState().memories).toEqual([original]);
  });
});

describe("authoritative hydration", () => {
  it("does not mark the product connected when health passes but tenant auth fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: string | URL | Request) => {
        const path = String(input);
        if (path.endsWith("/v1/health")) {
          return Response.json({ mp: "ok", hms: "ok", db: "ok" });
        }
        return Response.json(
          { detail: { code: "invalid_api_key" } },
          { status: 401, statusText: "Unauthorized" },
        );
      }),
    );

    const { useMemoryStore } = await import("@/store/memory-store");
    useMemoryStore.setState({
      hydrated: false,
      backendReachable: false,
      dataMode: "loading",
    });

    await useMemoryStore.getState().hydrate();

    expect(useMemoryStore.getState().hydrated).toBe(true);
    expect(useMemoryStore.getState().backendReachable).toBe(false);
  });
});
