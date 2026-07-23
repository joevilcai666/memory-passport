# Frontend gateway local run

The Next.js UI reaches Memory Passport through the same-origin `/api/mp/*`
product gateway. The browser never calls the FastAPI origin directly and never
receives a tenant API key.

For the local seeded stack:

```bash
cp .env.example .env
make demo
# In another terminal:
pnpm install
pnpm dev
```

`MP_API_URL` and `MP_API_KEY` are Next.js **server-only** runtime settings.
They must not be renamed with a `NEXT_PUBLIC_` prefix or placed in client code,
browser storage, page props, or request headers. The only browser-visible
configuration is the same-origin path owned by the application.

The current UI does not yet authenticate operators. Production mode therefore
keeps this gateway disabled unless `MP_GATEWAY_ALLOW_UNAUTHENTICATED=true` is
set explicitly. Use that override only for localhost or a trusted,
access-controlled evaluation network. Public deployment remains blocked on the
operator authentication/RBAC work in #32.

After `pnpm build`, the non-browser production tracer is:

```bash
pnpm test:gateway:production
```

It starts the production Next server against a stateful isolated upstream,
then proves load → versioned edit → reload → audit and scans delivered page/JS
assets for the tenant key. Issue #37 still owns the full browser release suite:
real click/typing automation, toast and loading-state assertions, and browser
storage/network inspection through browser instrumentation.
