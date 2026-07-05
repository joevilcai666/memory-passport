"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { QrCode, Check, Loader2, Camera } from "lucide-react";
import { AppShell } from "@/components/shell/AppShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";

export default function BindDevicePage() {
  const router = useRouter();
  const [pairingCode, setPairingCode] = React.useState("");
  const [scanning, setScanning] = React.useState(false);
  const [bound, setBound] = React.useState(false);

  const handleScan = () => {
    setScanning(true);
    setTimeout(() => {
      setScanning(false);
      setBound(true);
      toast.success("Luna Robot v1 detected", { description: "Ready to bind to your Passport." });
    }, 1800);
  };

  const handleBind = () => {
    toast.success("Device bound", {
      description: "Luna Robot v1 is now connected to your Passport.",
    });
    router.push("/app/devices");
  };

  return (
    <AppShell title="Bind device" backHref="/app/devices">
      <div className="space-y-6">
        {/* QR scanner mock */}
        <div className="rounded-2xl border bg-card p-5">
          <p className="text-sm font-medium">Scan the QR on your device</p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Found on the bottom of Luna Robot, or in its settings.
          </p>

          <div className="mt-4 flex aspect-square items-center justify-center rounded-xl border-2 border-dashed bg-muted/30">
            {bound ? (
              <div className="flex flex-col items-center gap-2 text-center">
                <div className="flex size-14 items-center justify-center rounded-full bg-emerald-500/15">
                  <Check className="size-7 text-emerald-600" strokeWidth={2} />
                </div>
                <p className="text-sm font-medium">Luna Robot v1</p>
                <p className="font-mono text-xs text-muted-foreground">SN a4f2…c891</p>
              </div>
            ) : scanning ? (
              <div className="flex flex-col items-center gap-3">
                <div className="relative">
                  <QrCode className="size-20 text-muted-foreground/40" strokeWidth={0.5} />
                  <div className="absolute inset-x-0 top-1/2 h-0.5 bg-primary shadow-[0_0_8px_var(--color-primary)] animate-[scan_1.8s_ease-in-out_infinite]" />
                </div>
                <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <Loader2 className="size-3 animate-spin" /> Scanning…
                </p>
              </div>
            ) : (
              <button
                onClick={handleScan}
                className="flex flex-col items-center gap-2 text-muted-foreground transition-colors hover:text-foreground"
              >
                <div className="flex size-14 items-center justify-center rounded-full bg-primary/10">
                  <Camera className="size-6 text-primary" strokeWidth={1.5} />
                </div>
                <p className="text-sm font-medium">Tap to scan</p>
              </button>
            )}
          </div>

          <style>{`@keyframes scan { 0%,100% { transform: translateY(-36px) } 50% { transform: translateY(36px) } }`}</style>
        </div>

        {/* Or pairing code */}
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <div className="h-px flex-1 bg-border" />
            <span className="text-xs text-muted-foreground">or enter code</span>
            <div className="h-px flex-1 bg-border" />
          </div>
          <Label htmlFor="pair" className="sr-only">Pairing code</Label>
          <Input
            id="pair"
            value={pairingCode}
            onChange={(e) => setPairingCode(e.target.value.toUpperCase())}
            placeholder="e.g. LUNA-4F2A"
            className="font-mono tracking-widest text-center"
          />
        </div>

        {/* Bind button */}
        <Button
          size="lg"
          className="w-full"
          disabled={!bound && pairingCode.length < 4}
          onClick={handleBind}
        >
          <Check className="size-4" />
          Bind to my Passport
        </Button>

        <p className="text-center text-[11px] text-muted-foreground/70">
          Binding links this device to your{" "}
          <span className="font-mono">passport_id</span>. You can unbind anytime.
        </p>
      </div>
    </AppShell>
  );
}
