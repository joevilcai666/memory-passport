import { afterEach, describe, expect, it, vi } from "vitest";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.resetModules();
});

describe("browser Memory Passport client", () => {
  it("edits through the same-origin gateway without a tenant credential", async () => {
    const authoritative = {
      id: "mem_version_2",
      content: "Authoritative content",
      version: 2,
      supersedes: "mem_version_1",
    };
    const browserFetch = vi.fn(async (input: string | URL | Request, init?: RequestInit) => {
      expect(input).toBe("/api/mp/v1/memories/mem_version_1");
      const headers = new Headers(init?.headers);
      expect(headers.has("authorization")).toBe(false);
      expect(init?.method).toBe("PATCH");
      return Response.json(authoritative);
    });
    vi.stubGlobal("fetch", browserFetch);

    const { api } = await import("@/lib/api-client");
    const result = await api.patchMemory("mem_version_1", {
      content: "Authoritative content",
    });

    expect(result).toEqual(authoritative);
    expect(browserFetch).toHaveBeenCalledOnce();
  });

  it("cannot turn a resource ID into a cross-origin request", async () => {
    const browserFetch = vi.fn(async (input: string | URL | Request) => {
      expect(input).toBe(
        "/api/mp/v1/memories/https%3A%2F%2Fattacker.test%2Fv1%2Fmemories%2Fmem_1",
      );
      return Response.json({ id: "mem_2", content: "saved", version: 2 });
    });
    vi.stubGlobal("fetch", browserFetch);

    const { api } = await import("@/lib/api-client");
    await api.patchMemory("https://attacker.test/v1/memories/mem_1", {
      content: "must stay same-origin",
    });
    expect(browserFetch).toHaveBeenCalledOnce();
  });
});
