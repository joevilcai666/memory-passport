"""MP tenant → HMS schema mapping (Slice N+).

Slice 1 ships exactly one tenant (Luna) and uses HMS's built-in
``ApiKeyTenantExtension`` with a single ``HMS_API_DATABASE_SCHEMA`` (``tenant_luna``).
Every HMS bank therefore lives under the Luna tenant's Postgres schema, which
satisfies the "under the Luna tenant's HMS schema" acceptance criterion.

The moment MP gains a second tenant we need a *custom* ``TenantExtension`` that
maps each MP tenant to a distinct ``TenantContext(schema_name=...)``. The HMS
extension contract (verified at the pinned commit ``a808ab393ca0``) is:

    class TenantExtension(Extension, ABC):
        async def authenticate(self, context: RequestContext) -> TenantContext: ...
        async def list_tenants(self) -> list[Tenant]: ...

where ``TenantContext`` is just ``@dataclass class TenantContext: schema_name: str``
and ``RequestContext`` carries ``api_key`` / ``api_key_id`` / ``tenant_id``.

Reference implementations ship with HMS:
* ``hms_api.extensions.builtin.tenant:ApiKeyTenantExtension`` (single-schema, what we use)
* ``hms_api.extensions.builtin.supabase_tenant`` (multi-tenant JWT)

The custom MP extension would resolve the MP tenant from the request (via a
shared header or the resolved MP TenantContext) and return
``TenantContext(schema_name=f"tenant_{mp_tenant_id}")``. ``ExtensionContext.run_migration``
provisions the schema on first sight. This is the documented next slice.
"""

# Intentionally no code — this module exists to record the plan in-place.
