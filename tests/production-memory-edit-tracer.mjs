import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createServer } from "node:http";
import { access } from "node:fs/promises";

const tenantKey = "mp_sandbox_LK39sn8vQ4x2pR7wY1tBz0Hd";
const initialMemory = {
  id: "mem_trace_v1",
  tenant_id: "ten_trace",
  app_id: "app_trace",
  passport_id: "pp_trace",
  user_id: "usr_trace",
  relationship_id: "rel_trace",
  agent_id: "agt_trace",
  device_id: null,
  type: "preference",
  content: "Original authoritative content",
  scope: "relationship_only",
  sensitivity: "S1",
  status: "active",
  confidence: 0.99,
  portability: {
    layer: "portable",
    cross_device: true,
    cross_role: true,
    cross_model: true,
    cross_brand_app: false,
  },
  source: {
    event_id: "evt_trace",
    source_type: "explicit_instruction",
    timestamp: "2026-07-22T00:00:00.000Z",
    quote: "Original authoritative content",
  },
  valid_from: "2026-07-22T00:00:00.000Z",
  expires_at: null,
  version: 1,
  supersedes: null,
  last_used_at: null,
  usage_count: 0,
  model_provenance: { created_by_model: "trace", retrieval_history: [] },
};

await access(new URL("../.next/BUILD_ID", import.meta.url)).catch(() => {
  throw new Error("Production build missing; run `pnpm build` before this tracer");
});

let currentMemory = initialMemory;
const audits = [];
const upstreamAuth = [];

function json(response, status, body) {
  response.writeHead(status, { "content-type": "application/json" });
  response.end(JSON.stringify(body));
}

async function readJson(request) {
  const chunks = [];
  for await (const chunk of request) chunks.push(chunk);
  return JSON.parse(Buffer.concat(chunks).toString("utf8"));
}

const upstream = createServer(async (request, response) => {
  upstreamAuth.push(request.headers.authorization ?? null);
  if (request.headers.authorization !== `Bearer ${tenantKey}`) {
    json(response, 401, { detail: { code: "invalid_api_key" } });
    return;
  }

  const url = new URL(request.url ?? "/", "http://upstream.test");
  if (request.method === "GET" && url.pathname === "/v1/memories") {
    json(response, 200, {
      items: [currentMemory],
      total: 1,
      page: 1,
      page_size: 100,
      pages: 1,
    });
    return;
  }
  if (
    request.method === "PATCH" &&
    url.pathname === `/v1/memories/${initialMemory.id}`
  ) {
    const { content } = await readJson(request);
    currentMemory = {
      ...initialMemory,
      id: "mem_trace_v2",
      content,
      version: 2,
      supersedes: initialMemory.id,
    };
    audits.unshift({
      id: "aud_trace_edit",
      tenant_id: "ten_trace",
      actor: "api:key_trace",
      action: "memory.edited",
      target: currentMemory.id,
      detail: `Edited memory ${initialMemory.id}; created version 2`,
      timestamp: "2026-07-22T00:01:00.000Z",
    });
    json(response, 200, currentMemory);
    return;
  }
  if (request.method === "GET" && url.pathname === "/v1/audit_logs") {
    json(response, 200, {
      items: audits,
      total: audits.length,
      page: 1,
      page_size: 100,
      pages: audits.length ? 1 : 0,
    });
    return;
  }
  json(response, 404, { detail: "not found" });
});

await new Promise((resolve) => upstream.listen(0, "127.0.0.1", resolve));
const upstreamAddress = upstream.address();
assert(upstreamAddress && typeof upstreamAddress !== "string");

const portProbe = createServer();
await new Promise((resolve) => portProbe.listen(0, "127.0.0.1", resolve));
const probeAddress = portProbe.address();
assert(probeAddress && typeof probeAddress !== "string");
const nextPort = probeAddress.port;
await new Promise((resolve, reject) =>
  portProbe.close((error) => (error ? reject(error) : resolve())),
);

const next = spawn(
  "pnpm",
  ["start", "--hostname", "127.0.0.1", "--port", String(nextPort)],
  {
    cwd: new URL("..", import.meta.url),
    env: {
      ...process.env,
      MP_API_URL: `http://127.0.0.1:${upstreamAddress.port}`,
      MP_API_KEY: tenantKey,
      MP_GATEWAY_ALLOW_UNAUTHENTICATED: "true",
    },
    stdio: ["ignore", "pipe", "pipe"],
  },
);

let serverOutput = "";
next.stdout.on("data", (chunk) => (serverOutput += chunk));
next.stderr.on("data", (chunk) => (serverOutput += chunk));

const productOrigin = `http://127.0.0.1:${nextPort}`;
async function waitForProduct() {
  const deadline = Date.now() + 30_000;
  while (Date.now() < deadline) {
    if (next.exitCode !== null) {
      throw new Error(`Next.js exited early:\n${serverOutput}`);
    }
    try {
      const response = await fetch(productOrigin);
      if (response.ok) return;
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error(`Timed out waiting for Next.js:\n${serverOutput}`);
}

async function browserRequest(path, init = {}) {
  const headers = new Headers(init.headers);
  assert.equal(headers.has("authorization"), false);
  const response = await fetch(`${productOrigin}${path}`, { ...init, headers });
  assert.equal(response.headers.has("authorization"), false);
  return response;
}

try {
  await waitForProduct();

  const page = await browserRequest(`/app/memory/${initialMemory.id}`);
  const html = await page.text();
  assert.equal(html.includes(tenantKey), false, "tenant key leaked into page source");
  const scriptPaths = [...html.matchAll(/<script[^>]+src="([^"]+\.js[^"]*)"/g)].map(
    ([, path]) => path,
  );
  assert(scriptPaths.length > 0, "expected production JavaScript assets");
  for (const scriptPath of new Set(scriptPaths)) {
    const script = await browserRequest(scriptPath);
    const source = await script.text();
    assert.equal(
      source.includes(tenantKey),
      false,
      `tenant key leaked into ${scriptPath}`,
    );
  }

  const loaded = await browserRequest("/api/mp/v1/memories?page_size=100");
  assert.equal(loaded.status, 200);
  assert.equal((await loaded.json()).items[0].content, initialMemory.content);

  const editedContent = "Persisted through the production gateway";
  const edited = await browserRequest(
    `/api/mp/v1/memories/${initialMemory.id}`,
    {
      method: "PATCH",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ content: editedContent }),
    },
  );
  assert.equal(edited.status, 200);
  const returned = await edited.json();
  assert.equal(returned.id, "mem_trace_v2");
  assert.equal(returned.version, 2);
  assert.equal(returned.content, editedContent);

  const reloaded = await browserRequest("/api/mp/v1/memories?page_size=100");
  const persisted = (await reloaded.json()).items[0];
  assert.deepEqual(
    { id: persisted.id, version: persisted.version, content: persisted.content },
    { id: returned.id, version: returned.version, content: returned.content },
  );

  const auditResponse = await browserRequest(
    "/api/mp/v1/audit_logs?action=memory.edited&page_size=100",
  );
  const audit = (await auditResponse.json()).items[0];
  assert.equal(audit.action, "memory.edited");
  assert.equal(audit.target, returned.id);

  const directHeaders = { authorization: `Bearer ${tenantKey}` };
  const directMemoryResponse = await fetch(
    `http://127.0.0.1:${upstreamAddress.port}/v1/memories?page_size=100`,
    { headers: directHeaders },
  );
  const directMemory = (await directMemoryResponse.json()).items[0];
  assert.deepEqual(
    {
      id: directMemory.id,
      version: directMemory.version,
      content: directMemory.content,
    },
    { id: returned.id, version: returned.version, content: returned.content },
  );
  const directAuditResponse = await fetch(
    `http://127.0.0.1:${upstreamAddress.port}/v1/audit_logs?action=memory.edited&page_size=100`,
    { headers: directHeaders },
  );
  const directAudit = (await directAuditResponse.json()).items[0];
  assert.equal(directAudit.action, "memory.edited");
  assert.equal(directAudit.target, returned.id);
  assert(upstreamAuth.length >= 4);
  assert(upstreamAuth.every((value) => value === `Bearer ${tenantKey}`));

  console.log(
    "PASS production gateway tracer: load → edit → reload → audit; tenant key absent from browser requests/page/assets",
  );
} finally {
  next.kill("SIGTERM");
  await new Promise((resolve) => upstream.close(resolve));
}
