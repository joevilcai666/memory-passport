"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Check, Cpu, KeyRound, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { AppShell } from "@/components/shell/AppShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { DeviceRegisterResult } from "@/lib/types";
import { useMemoryStore } from "@/store/memory-store";

export default function BindDevicePage() {
  const router = useRouter();
  const devices = useMemoryStore((state) => state.devices);
  const currentUser = useMemoryStore((state) => state.currentUser);
  const dataMode = useMemoryStore((state) => state.dataMode);
  const registerDevice = useMemoryStore((state) => state.registerDevice);
  const bindDevice = useMemoryStore((state) => state.bindDevice);
  const [pairingCode, setPairingCode] = React.useState("");
  const [registeredResult, setRegisteredResult] = React.useState<DeviceRegisterResult | null>(null);
  const [registering, setRegistering] = React.useState(false);
  const [binding, setBinding] = React.useState(false);

  const targetDevice =
    registeredResult?.device ?? devices.find((device) => device.status === "registered");
  const effectivePairingCode = registeredResult?.pairing_code ?? pairingCode.trim().toUpperCase();

  const handleRegister = async () => {
    setRegistering(true);
    try {
      const result = await registerDevice({
        model: "Luna Robot",
        generation: "v2",
        serial_number_hash: `local-evaluation-${Date.now().toString(36)}`,
      });
      setRegisteredResult(result);
      setPairingCode(result.pairing_code);
      toast.success("Device registered", {
        description: "Use the one-time pairing code below to bind it.",
      });
    } catch (error) {
      toast.error("Could not register device", {
        description: error instanceof Error ? error.message : "Please try again.",
      });
    } finally {
      setRegistering(false);
    }
  };

  const handleBind = async () => {
    if (!targetDevice || !effectivePairingCode) return;

    setBinding(true);
    try {
      const boundDevice = await bindDevice({
        device_id: targetDevice.id,
        user_id: currentUser.id,
        pairing_code: effectivePairingCode,
      });
      toast.success("Device bound", {
        description: `${boundDevice.model} ${boundDevice.generation} is now connected to your Passport.`,
      });
      router.push("/app/devices");
    } catch (error) {
      toast.error("Could not bind device", {
        description: error instanceof Error ? error.message : "Please check the pairing code.",
      });
    } finally {
      setBinding(false);
    }
  };

  return (
    <AppShell title="Bind device" backHref="/app/devices">
      <div className="space-y-6">
        <div className="rounded-2xl border bg-card p-5">
          <div className="flex items-start gap-3">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-full bg-primary/10">
              <Cpu className="size-5 text-primary" strokeWidth={1.5} />
            </div>
            <div>
              <p className="text-sm font-medium">Register a test device</p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                This local evaluation flow creates a real device record and one-time pairing code.
                Camera and QR scanning are not available in this build.
              </p>
            </div>
          </div>

          <Button
            type="button"
            variant="outline"
            className="mt-4 w-full"
            onClick={handleRegister}
            disabled={registering || binding || dataMode !== "live"}
          >
            {registering ? <Loader2 className="size-4 animate-spin" /> : <KeyRound className="size-4" />}
            {registering ? "Registering..." : "Register test device"}
          </Button>

          {registeredResult ? (
            <div className="mt-4 rounded-xl border bg-muted/30 p-4 text-center">
              <p className="text-sm font-medium">
                {registeredResult.device.model} {registeredResult.device.generation}
              </p>
              <p className="mt-1 font-mono text-xs text-muted-foreground">
                {registeredResult.device.id}
              </p>
              <p className="mt-3 text-xs text-muted-foreground">One-time pairing code</p>
              <p className="mt-1 font-mono text-lg font-semibold tracking-widest">
                {registeredResult.pairing_code}
              </p>
            </div>
          ) : null}
        </div>

        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <div className="h-px flex-1 bg-border" />
            <span className="text-xs text-muted-foreground">or enter an issued code</span>
            <div className="h-px flex-1 bg-border" />
          </div>
          <Label htmlFor="pair" className="sr-only">
            Pairing code
          </Label>
          <Input
            id="pair"
            value={pairingCode}
            onChange={(event) => {
              setRegisteredResult(null);
              setPairingCode(event.target.value.toUpperCase());
            }}
            placeholder="e.g. LUNA-4F2A"
            className="text-center font-mono tracking-widest"
          />
        </div>

        <Button
          size="lg"
          className="w-full"
          disabled={
            !targetDevice || effectivePairingCode.length < 4 || binding || registering || dataMode !== "live"
          }
          onClick={handleBind}
        >
          {binding ? <Loader2 className="size-4 animate-spin" /> : <Check className="size-4" />}
          {binding ? "Binding..." : "Bind to my Passport"}
        </Button>

        {dataMode !== "live" ? (
          <p className="text-center text-xs text-amber-700">
            Connect to the backend before registering or binding a device.
          </p>
        ) : null}

        <p className="text-center text-[11px] text-muted-foreground/70">
          Binding links this device to your <span className="font-mono">passport_id</span>. You can
          unbind anytime.
        </p>
      </div>
    </AppShell>
  );
}
