import "server-only";

const PRODUCT_ENDPOINTS: Readonly<Record<string, readonly RegExp[]>> = {
  GET: [
    /^v1\/health$/,
    /^v1\/apps$/,
    /^v1\/apps\/[^/]+$/,
    /^v1\/memories$/,
    /^v1\/audit_logs$/,
    /^v1\/usage$/,
    /^v1\/policies$/,
    /^v1\/migrations\/[^/]+$/,
    /^v1\/exports\/[^/]+$/,
    // Token-gated one-shot download (no tenant credential needed; auth is the
    // single-use query token issued by the export status endpoint).
    /^v1\/exports\/[^/]+\/download$/,
    /^v1\/team$/,
    /^v1\/debug\/traces\/[^/]+$/,
    // Public (unauthenticated) single-use invite preview by token.
    /^v1\/public\/team-invites\/[^/]+$/,
  ],
  POST: [
    /^v1\/apps$/,
    /^v1\/apps\/[^/]+\/api-keys$/,
    /^v1\/apps\/[^/]+\/api-keys\/[^/]+\/rotate$/,
    /^v1\/users$/,
    /^v1\/events\/ingest$/,
    /^v1\/memories\/retrieve$/,
    /^v1\/policies$/,
    /^v1\/migrations\/(?:preview|execute)$/,
    /^v1\/migrations\/[^/]+\/rollback$/,
    /^v1\/exports$/,
    /^v1\/delete_user$/,
    /^v1\/devices\/(?:register|bind|unbind|wipe)$/,
    /^v1\/team\/invites$/,
    // Public (unauthenticated) single-use invite acceptance by token.
    /^v1\/public\/team-invites\/[^/]+\/accept$/,
    /^v1\/debug\/traces\/[^/]+\/feedback$/,
  ],
  PATCH: [
    /^v1\/memories\/[^/]+$/,
    /^v1\/users\/[^/]+\/consent$/,
  ],
  DELETE: [/^v1\/memories\/[^/]+$/],
};

function errorResponse(status: number, code: string, message: string) {
  return Response.json(
    { error: { code, message } },
    { status, headers: { "cache-control": "no-store" } },
  );
}

function serverConfig() {
  const baseUrl = process.env.MP_API_URL;
  const apiKey = process.env.MP_API_KEY;
  if (
    process.env.NODE_ENV === "production" &&
    process.env.MP_GATEWAY_ALLOW_UNAUTHENTICATED !== "true"
  ) {
    throw new Error("Unauthenticated MP gateway is disabled in production");
  }
  if (!baseUrl || !apiKey) {
    throw new Error("Memory Passport server configuration is incomplete");
  }
  const url = new URL(baseUrl);
  if (url.protocol !== "http:" && url.protocol !== "https:") {
    throw new Error("Memory Passport server URL must use HTTP(S)");
  }
  return { url, apiKey };
}

/**
 * Server-only product seam between browser requests and Memory Passport.
 * Callers supply a same-origin request and an already-decoded route path; the
 * module owns endpoint authorization, credentials, timeouts, and safe headers.
 */
export async function forwardMpRequest(
  request: Request,
  path: string[],
): Promise<Response> {
  const pathname = path.join("/");
  const allowed = PRODUCT_ENDPOINTS[request.method]?.some((pattern) =>
    pattern.test(pathname),
  );
  if (!allowed) {
    return errorResponse(404, "not_found", "Product endpoint not found");
  }

  let config: ReturnType<typeof serverConfig>;
  try {
    config = serverConfig();
  } catch {
    return errorResponse(
      503,
      "mp_unavailable",
      "Memory Passport is not configured",
    );
  }

  const incomingUrl = new URL(request.url);
  const upstreamUrl = new URL(`/${pathname}`, config.url);
  upstreamUrl.search = incomingUrl.search;

  const headers = new Headers({
    authorization: `Bearer ${config.apiKey}`,
    accept: "application/json",
  });
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);

  try {
    const body =
      request.method === "GET" || request.method === "HEAD"
        ? undefined
        : await request.arrayBuffer();
    const upstream = await fetch(
      new Request(upstreamUrl, {
        method: request.method,
        headers,
        body,
        cache: "no-store",
        redirect: "manual",
        signal: AbortSignal.timeout(10_000),
      }),
    );
    const responseHeaders = new Headers({ "cache-control": "no-store" });
    const responseType = upstream.headers.get("content-type");
    if (responseType) responseHeaders.set("content-type", responseType);
    return new Response(upstream.body, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: responseHeaders,
    });
  } catch {
    return errorResponse(
      503,
      "mp_unavailable",
      "Memory Passport is temporarily unavailable",
    );
  }
}
