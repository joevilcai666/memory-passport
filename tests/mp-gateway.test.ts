// @vitest-environment node

// @vitest-environment node
// The gateway forwards real Request/Response objects with an AbortSignal timeout.
// jsdom's Request rejects Node's AbortSignal, so this file must run under node.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));

beforeEach(() => {
  vi.stubEnv("NODE_ENV", "test");
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
  vi.resetModules();
});

describe("same-origin Memory Passport gateway", () => {
  it("fails closed in production without an explicit trusted-network override", async () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("MP_API_URL", "http://memory-passport.internal:8000");
    vi.stubEnv("MP_API_KEY", "mp_server_only_test_secret");
    const upstream = vi.fn();
    vi.stubGlobal("fetch", upstream);

    const { GET } = await import("@/app/api/mp/[...path]/route");
    const response = await GET(
      new Request("http://product.test/api/mp/v1/memories?page_size=100"),
      { params: Promise.resolve({ path: ["v1", "memories"] }) },
    );

    expect(response.status).toBe(503);
    expect(upstream).not.toHaveBeenCalled();
  });

  it("returns the authoritative memory while keeping the tenant credential server-side", async () => {
    vi.stubEnv("MP_API_URL", "http://memory-passport.internal:8000");
    vi.stubEnv("MP_API_KEY", "mp_server_only_test_secret");

    const returnedMemory = {
      id: "mem_version_2",
      content: "The server-returned edit",
      version: 2,
      supersedes: "mem_version_1",
    };
    const upstream = vi.fn(async (request: Request) => {
      expect(request.url).toBe(
        "http://memory-passport.internal:8000/v1/memories/mem_version_1",
      );
      expect(request.method).toBe("PATCH");
      expect(request.headers.get("authorization")).toBe(
        "Bearer mp_server_only_test_secret",
      );
      expect(await request.json()).toEqual({ content: "The server-returned edit" });
      return Response.json(returnedMemory);
    });
    vi.stubGlobal("fetch", upstream);

    const { PATCH } = await import("@/app/api/mp/[...path]/route");
    const response = await PATCH(
      new Request(
        "http://product.test/api/mp/v1/memories/mem_version_1",
        {
          method: "PATCH",
          headers: {
            authorization: "Bearer browser-supplied-key-must-be-ignored",
            "content-type": "application/json",
          },
          body: JSON.stringify({ content: "The server-returned edit" }),
        },
      ),
      {
        params: Promise.resolve({
          path: ["v1", "memories", "mem_version_1"],
        }),
      },
    );

    expect(upstream).toHaveBeenCalledOnce();
    expect({ status: response.status, body: await response.json() }).toEqual({
      status: 200,
      body: returnedMemory,
    });
    expect(response.headers.get("authorization")).toBeNull();
  });

  it("forwards an allowed product read with its query string", async () => {
    vi.stubEnv("MP_API_URL", "http://memory-passport.internal:8000");
    vi.stubEnv("MP_API_KEY", "mp_server_only_test_secret");
    vi.stubGlobal(
      "fetch",
      vi.fn(async (request: Request) => {
        expect(request.url).toBe(
          "http://memory-passport.internal:8000/v1/memories?page_size=100",
        );
        expect(request.method).toBe("GET");
        return Response.json({ items: [], total: 0, page: 1, page_size: 100, pages: 0 });
      }),
    );

    const { GET } = await import("@/app/api/mp/[...path]/route");
    const response = await GET(
      new Request("http://product.test/api/mp/v1/memories?page_size=100"),
      { params: Promise.resolve({ path: ["v1", "memories"] }) },
    );

    expect(response.status).toBe(200);
    expect((await response.json()).items).toEqual([]);
  });

  it("preserves an upstream authorization failure for the browser", async () => {
    vi.stubEnv("MP_API_URL", "http://memory-passport.internal:8000");
    vi.stubEnv("MP_API_KEY", "invalid-server-key");
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        Response.json(
          { detail: { code: "invalid_api_key", message: "Invalid API key" } },
          { status: 401 },
        ),
      ),
    );

    const { PATCH } = await import("@/app/api/mp/[...path]/route");
    const response = await PATCH(
      new Request("http://product.test/api/mp/v1/memories/mem_version_1", {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ content: "Must not look saved" }),
      }),
      {
        params: Promise.resolve({
          path: ["v1", "memories", "mem_version_1"],
        }),
      },
    );

    expect(response.status).toBe(401);
    expect(await response.json()).toEqual({
      detail: { code: "invalid_api_key", message: "Invalid API key" },
    });
  });

  it("returns an explicit 503 when the backend is stopped", async () => {
    vi.stubEnv("MP_API_URL", "http://127.0.0.1:1");
    vi.stubEnv("MP_API_KEY", "mp_server_only_test_secret");
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("fetch failed");
      }),
    );

    const { GET } = await import("@/app/api/mp/[...path]/route");
    const response = await GET(
      new Request("http://product.test/api/mp/v1/memories?page_size=100"),
      { params: Promise.resolve({ path: ["v1", "memories"] }) },
    );

    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({
      error: {
        code: "mp_unavailable",
        message: "Memory Passport is temporarily unavailable",
      },
    });
  });
});
