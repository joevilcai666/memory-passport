"""Tenant, App, ApiKey — the B-side ownership graph.

Mirrors ``Tenant`` / ``App`` / ``ApiKey`` in ``src/lib/types.ts``.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import (
    PG_APP_STATUS,
    PG_DATA_REGION,
    PG_ENVIRONMENT,
    PG_PRODUCT_TYPE,
    PG_TENANT_PLAN,
    AppStatus,
    DataRegion,
    Environment,
    ProductType,
    TenantPlan,
)
from app.services.ids import new_hms_key, tenant_hms_schema


def _default_hms_schema(context) -> str:
    """Default schema name = ``tenant_<id>``; the seeded Luna row overrides it."""
    params = context.get_current_parameters()
    return tenant_hms_schema(params["id"])


class Tenant(Base):
    """A customer. Owns apps, users, and all memory under them."""

    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    plan: Mapped[TenantPlan] = mapped_column(
        PG_TENANT_PLAN, nullable=False, default=TenantPlan.SANDBOX
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    # Per-tenant HMS credentials (issue #12). MP sends ``hms_api_key`` as the
    # Bearer token when calling HMS; the custom MPTenantExtension maps it to
    # ``hms_schema`` (a distinct Postgres schema under the shared HMS DB).
    # Lazily provisioned on first ``create_app`` for a tenant; the seeded Luna
    # tenant is backfilled with the legacy shared key + ``tenant_luna`` schema.
    # Both default so bare ``Tenant(...)`` constructions in tests/seeds keep
    # working without caring about the multi-tenant detail.
    hms_api_key: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True, default=new_hms_key
    )
    hms_schema: Mapped[str] = mapped_column(
        String(64), nullable=False, default=_default_hms_schema
    )

    apps: Mapped[list[App]] = relationship(back_populates="tenant", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Tenant {self.id}>"


class App(Base):
    """An app under a tenant. Carries branding + environment scope."""

    __tablename__ = "apps"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_type: Mapped[ProductType] = mapped_column(PG_PRODUCT_TYPE, nullable=False)
    environment: Mapped[Environment] = mapped_column(PG_ENVIRONMENT, nullable=False)
    data_region: Mapped[DataRegion] = mapped_column(PG_DATA_REGION, nullable=False)
    show_powered_by: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[AppStatus] = mapped_column(
        PG_APP_STATUS, nullable=False, default=AppStatus.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False)

    tenant: Mapped[Tenant] = relationship(back_populates="apps")
    api_keys: Mapped[list[ApiKey]] = relationship(
        back_populates="app", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<App {self.id}>"


class ApiKey(Base):
    """A per-environment API key on an app. The bearer token in MP auth."""

    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    app_id: Mapped[str] = mapped_column(
        ForeignKey("apps.id", ondelete="CASCADE"), nullable=False, index=True
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    environment: Mapped[Environment] = mapped_column(PG_ENVIRONMENT, nullable=False)
    # mp_<env>_<secret>. Unique — this is what the auth middleware looks up.
    key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(nullable=True)

    app: Mapped[App] = relationship(back_populates="api_keys")

    __table_args__ = (
        Index("ix_api_keys_key", "key"),
    )

    def __repr__(self) -> str:
        return f"<ApiKey {self.id} ({self.environment})>"
