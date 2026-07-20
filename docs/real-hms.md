# Real HMS Inference

Memory Passport uses the same `HmsClient` paths in demo and real modes. The
real overlay replaces the deterministic `hms-api` service with the pinned HMS
submodule image and adds its worker; MP's domain behavior does not change.

## Prerequisites

```bash
git submodule update --init --recursive
cp .env.example .env
```

Use provider credentials that are authorized for inference and embedding
calls. Real mode can incur provider charges.

## Required credentials

All three must be non-empty and must not end in `_change_me`:

```dotenv
HMS_API_LLM_API_KEY=...
HMS_API_RETAIN_LLM_API_KEY=...
HMS_API_EMBEDDINGS_OPENAI_API_KEY=...
```

The first configures HMS's general LLM path, the second its retain/fact
extraction path, and the third its embedding path. They may be the same secret
if the selected provider permits it, but the three settings are validated
independently.

Provider/model settings:

```dotenv
HMS_API_LLM_PROVIDER=openai
HMS_API_LLM_MODEL=gpt-4o
HMS_API_LLM_BASE_URL=

HMS_API_RETAIN_LLM_PROVIDER=openai
HMS_API_RETAIN_LLM_MODEL=gpt-4o
HMS_API_RETAIN_LLM_BASE_URL=

HMS_API_EMBEDDINGS_PROVIDER=openai
HMS_API_EMBEDDINGS_OPENAI_MODEL=text-embedding-3-small
HMS_API_EMBEDDINGS_OPENAI_BASE_URL=

HMS_API_RERANKER_PROVIDER=rrf
HMS_API_SKIP_LLM_VERIFICATION=false
```

For an OpenAI-compatible provider, set the matching base URL and provider/model
values supported by the pinned HMS commit. Never commit `.env`.

## Validate and start

```bash
make real-config   # validates keys and renders the merged Compose config
make real-up       # builds/starts postgres, HMS API, HMS worker, and MP
```

Equivalent explicit command:

```bash
./scripts/validate-real-hms-env.sh
docker-compose -f docker-compose.yml -f docker-compose.real.yml up -d --wait
```

The Makefile automatically uses `docker compose` when available.

Placeholder credentials intentionally fail before containers start:

```text
real HMS mode requires a non-placeholder HMS_API_LLM_API_KEY; see docs/real-hms.md
```

MP also validates the three credentials during application startup whenever
`MP_MEMORY_ENGINE_MODE=real`.

## Verify the real path

```bash
curl -s http://127.0.0.1:8000/v1/health | python3 -m json.tool
```

Expected MP fields include:

```json
{"mp":"ok","hms":"ok","db":"ok","memory_engine":"real"}
```

Then send an ingest and retrieve request from
[`local-evaluation.md`](local-evaluation.md). In real mode, retain invokes the
configured extraction LLM and embeddings, and recall uses the persisted HMS
vectors. Confirm both services are healthy:

```bash
docker-compose -f docker-compose.yml -f docker-compose.real.yml ps
docker-compose -f docker-compose.yml -f docker-compose.real.yml logs --tail=200 hms-api hms-worker
```

To return to the credential-free evaluator:

```bash
make real-down
make up
```

The base stack removes the real-only worker as an orphan. Database volumes are
preserved unless `make clean` is used.

## Security notes

- Provider keys are passed only to HMS and to MP's startup validator; MP does
  not expose them through APIs or export bundles.
- The real overlay is pinned to `vendor/hms`; update the submodule deliberately
  and rerun the complete local gate after any pin change.
- `HMS_API_SKIP_LLM_VERIFICATION=true` bypasses HMS's startup probe but does not
  bypass MP's non-placeholder validation or the provider calls made by retain.
