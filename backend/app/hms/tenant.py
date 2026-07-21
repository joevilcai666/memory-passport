"""MP tenant → HMS schema mapping (issue #12).

Status: **implemented**. Slice 1 shipped exactly one HMS tenant (Luna) using
HMS's built-in ``ApiKeyTenantExtension`` with a single ``HMS_API_DATABASE_SCHEMA``
(``tenant_luna``). This slice adds true multi-tenancy: each MP tenant maps to
its own HMS schema, auto-provisioned on first ingest.

Design
------
* MP stores a per-tenant HMS API key (``tenants.hms_api_key``) + schema name
  (``tenants.hms_schema``). Migration ``0009_tenant_hms_credentials`` adds the
  columns and backfills the Luna tenant with the legacy shared key +
  ``tenant_luna`` (so existing data keeps working).
* When MP calls HMS it forwards the caller tenant's key as the Bearer token
  (see :func:`app.hms.hms_client_for_tenant`). The MP↔HMS HTTP contract
  (:class:`app.hms.HmsClient`) is **unchanged** — only the bearer key +
  tenant→schema resolution change.
* The custom HMS extension :class:`hms_api.extensions.builtin.mp_tenant.MPTenantExtension`
  (in the vendored HMS fork at ``vendor/hms``) resolves the key → schema via an
  env-loaded map (``HMS_API_TENANT_KEYS=key1=schema1,key2=schema2,...``) and
  calls ``context.run_migration(schema)`` on first sight to create the schema
  + replay HMS's migrations into it (idempotent, per-schema advisory lock).
* Provisioning: :func:`app.services.provisioning.provision_tenant_hms_credentials`
  mints the key + schema for a tenant that doesn't have them yet; called from
  ``create_app`` (idempotent) so onboarding a new tenant + app is automatic.

Deployment
----------
* Demo mode (``docker-compose.yml``) is unchanged — the demo HMS is single-schema
  by design and ignores the key.
* Real mode (``docker-compose.real.yml``) now sets
  ``HMS_API_TENANT_EXTENSION=hms_api.extensions.builtin.mp_tenant:MPTenantExtension``
  + ``HMS_API_TENANT_KEYS`` (defaulted to the Luna pair). Onboarding a new
  tenant means minting a key on the MP side and adding ``<new_key>=tenant_<id>``
  to ``HMS_API_TENANT_KEYS`` in ``.env`` (then ``make real-up``).

Tests
-----
* ``backend/tests/test_provisioning.py`` — creating an App under a fresh
  tenant mints the key + schema; the seeded Luna tenant keeps ``tenant_luna``.
* ``backend/tests/test_multi_tenant_hms.py`` — parametrized isolation: tenant
  A's HMS client carries ``hms_api_key_A``, tenant B's carries ``hms_api_key_B``.
* The fork's ``core/dataplane/tests/test_mp_tenant.py`` — the HMS-side
  key→schema resolution + lazy provisioning + sanitization.
* Compose-level cross-schema isolation stays manual (needs the real HMS image)
  — see ``docs/real-hms.md``.
"""

# This module records the design in-place; the implementation lives in the
# services / models / the forked HMS extension noted above.
