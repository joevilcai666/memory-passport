"use client";

import Link from "next/link";
import { Plus, Smartphone, Cpu, ArrowRight, CircleCheck } from "lucide-react";
import { AppShell } from "@/components/shell/AppShell";
import { Badge } from "@/components/ui/badge";
import { useMemoryStore } from "@/store/memory-store";
import { formatRelativeDay } from "@/lib/utils";
import type { Device } from "@/lib/types";

export default function DevicesPage() {
  const { devices, currentUser, migration } = useMemoryStore();

  // Show devices bound to the current user + the v2 (registered, awaiting bind)
  const myDevices = devices.filter(
    (d) => d.bound_user_id === currentUser.id || d.status === "registered",
  );

  const migrated = migration.status === "completed";

  return (
    <AppShell title="Devices" backHref="/app/memory">
      <div className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Devices bound to your Passport. Memories travel between them.
        </p>

        {/* Migration banner if v2 is pending or done */}
        {(migration.status === "preview" || migrated) && (
          <Link
            href={migrated ? "/app/migrate/complete" : "/app/migrate"}
            className="block rounded-2xl border border-primary/30 bg-primary/5 p-4 transition-colors hover:bg-primary/10"
          >
            <div className="flex items-center gap-3">
              <div className="flex size-10 items-center justify-center rounded-xl bg-primary/15">
                <Cpu className="size-5 text-primary" strokeWidth={1.5} />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-foreground">
                  {migrated ? "Migration complete" : "Luna Robot v2 ready"}
                </p>
                <p className="text-xs text-muted-foreground">
                  {migrated
                    ? "Your memories are now on v2."
                    : "Move your memories from v1 → v2. The wedge."}
                </p>
              </div>
              <ArrowRight className="size-4 text-primary" />
            </div>
          </Link>
        )}

        {/* Device list */}
        <div className="space-y-2.5">
          {myDevices.map((d) => (
            <DeviceRow key={d.id} device={d} />
          ))}
        </div>

        {/* Bind new */}
        <Link
          href="/app/devices/bind"
          className="block rounded-2xl border border-dashed p-5 text-center transition-colors hover:border-primary/40 hover:bg-primary/5"
        >
          <div className="mx-auto flex size-10 items-center justify-center rounded-xl bg-muted">
            <Plus className="size-5 text-muted-foreground" strokeWidth={1.5} />
          </div>
          <p className="mt-2 text-sm font-medium">Bind a new device</p>
          <p className="mt-0.5 text-xs text-muted-foreground">Scan a QR or enter a pairing code</p>
        </Link>
      </div>
    </AppShell>
  );
}

function DeviceRow({ device }: { device: Device }) {
  const isV2 = device.generation === "v2";
  const bound = device.status === "bound";
  return (
    <div className="rounded-2xl border bg-card p-4">
      <div className="flex items-center gap-3">
        <div className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-primary/10">
          <Smartphone className="size-5 text-primary" strokeWidth={1.5} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <p className="text-sm font-medium">{device.model} {device.generation}</p>
            {bound && (
              <Badge variant="success" className="gap-1 text-[10px]">
                <CircleCheck className="size-2.5" /> Bound
              </Badge>
            )}
            {!bound && <Badge variant="outline" className="text-[10px]">Registered</Badge>}
            {isV2 && <Badge variant="ink" className="text-[10px]">New</Badge>}
          </div>
          <p className="mt-0.5 font-mono text-[11px] text-muted-foreground">
            SN {device.serial_number_hash}
          </p>
          {device.last_seen_at && (
            <p className="text-[11px] text-muted-foreground/70">
              last seen {formatRelativeDay(device.last_seen_at)}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
