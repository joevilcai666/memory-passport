"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Bot, Cpu, Layers, Check, ArrowRight, Copy, Loader2 } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { PoweredByMemoryPassport } from "@/components/brand/PoweredByMemoryPassport";
import { cn } from "@/lib/utils";
import { useMemoryStore } from "@/store/memory-store";
import { toast } from "sonner";
import type { Environment, ProductType } from "@/lib/types";

const productTypes: { value: ProductType; icon: typeof Bot; title: string; desc: string }[] = [
  { value: "software", icon: Bot, title: "Software companion", desc: "AI friend, character, mood companion, or pet app." },
  { value: "hardware", icon: Cpu, title: "Robot hardware", desc: "Companion robot, AI pet, desktop robot, bionic OEM." },
  { value: "hybrid", icon: Layers, title: "Hybrid", desc: "A companion with both an app and a robot body (like Luna)." },
];

export default function NewAppPage() {
  const router = useRouter();
  const createApp = useMemoryStore((state) => state.createApp);
  const [name, setName] = React.useState("");
  const [productType, setProductType] = React.useState<ProductType>("hybrid");
  const [environment, setEnvironment] = React.useState<Environment>("sandbox");
  const [region, setRegion] = React.useState<"us-east-1" | "eu-west-1" | "ap-southeast-1">("us-east-1");
  const [showPoweredBy, setShowPoweredBy] = React.useState(true);
  const [creating, setCreating] = React.useState(false);
  const [createdKey, setCreatedKey] = React.useState<string | null>(null);

  const canCreate = name.trim().length > 0;

  const handleCreate = async () => {
    if (!canCreate || creating) return;
    setCreating(true);
    try {
      const result = await createApp({
        name: name.trim(),
        product_type: productType,
        environment,
        data_region: region,
        show_powered_by: showPoweredBy,
      });
      setCreatedKey(result.api_key.key);
    } catch (error) {
      toast.error("App creation failed", {
        description: error instanceof Error ? error.message : "Unknown error",
      });
    } finally {
      setCreating(false);
    }
  };

  const copyCreatedKey = async () => {
    if (!createdKey) return;
    try {
      await navigator.clipboard.writeText(createdKey);
      toast.success("API key copied");
    } catch (error) {
      toast.error("Could not copy API key", {
        description: error instanceof Error ? error.message : "Clipboard unavailable",
      });
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-medium tracking-tight">Create app</h1>
        <p className="mt-0.5 text-sm text-muted-foreground">
          Configure a new product surface. You can change most of this later.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <div className="space-y-6">
          {/* App name */}
          <Card>
            <CardHeader>
              <CardTitle>App name</CardTitle>
              <CardDescription>Shown in the console and to your team.</CardDescription>
            </CardHeader>
            <CardContent>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Luna"
                className="max-w-sm"
              />
            </CardContent>
          </Card>

          {/* Product type */}
          <Card>
            <CardHeader>
              <CardTitle>Product type</CardTitle>
              <CardDescription>
                Determines which SDK surfaces and migration flows are enabled.
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3 sm:grid-cols-3">
              {productTypes.map((pt) => {
                const selected = productType === pt.value;
                const Icon = pt.icon;
                return (
                  <button
                    key={pt.value}
                    onClick={() => setProductType(pt.value)}
                    className={cn(
                      "rounded-xl border p-4 text-left transition-all",
                      selected
                        ? "border-primary bg-primary/5 ring-1 ring-primary"
                        : "hover:border-foreground/20",
                    )}
                  >
                    <div className="flex items-center justify-between">
                      <Icon
                        className={cn("size-5", selected ? "text-primary" : "text-muted-foreground")}
                        strokeWidth={1.5}
                      />
                      {selected && (
                        <div className="flex size-5 items-center justify-center rounded-full bg-primary text-primary-foreground">
                          <Check className="size-3" />
                        </div>
                      )}
                    </div>
                    <p className="mt-3 text-sm font-medium">{pt.title}</p>
                    <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{pt.desc}</p>
                  </button>
                );
              })}
            </CardContent>
          </Card>

          {/* Environment + region */}
          <Card>
            <CardHeader>
              <CardTitle>Environment</CardTitle>
              <CardDescription>Start in sandbox. Promote to production when ready.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label>Environment</Label>
                <Select value={environment} onValueChange={(value) => setEnvironment(value as Environment)}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="sandbox">Sandbox</SelectItem>
                    <SelectItem value="production">Production</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>Data region</Label>
                <Select value={region} onValueChange={(value) => setRegion(value as typeof region)}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="us-east-1">us-east-1</SelectItem>
                    <SelectItem value="eu-west-1">eu-west-1</SelectItem>
                    <SelectItem value="ap-southeast-1">ap-southeast-1</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          {/* Branding */}
          <Card>
            <CardHeader>
              <CardTitle>Branding</CardTitle>
              <CardDescription>
                The co-brand watermark seeds user awareness that memory is portable
                and theirs. White-label arrives in P1.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-start justify-between gap-4 rounded-lg border p-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Label className="text-sm font-medium">Show &ldquo;Powered by Memory Passport&rdquo;</Label>
                    {showPoweredBy && <Badge variant="ink" className="text-[10px]">Recommended</Badge>}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Appears on consent, Memory Center, and migration complete.
                  </p>
                </div>
                <Switch checked={showPoweredBy} onCheckedChange={setShowPoweredBy} />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Live preview + actions */}
        <div className="space-y-4 lg:sticky lg:top-32 lg:self-start">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Preview</CardTitle>
              <CardDescription>How consent will look to your users.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="paper-surface rounded-xl border bg-background p-5">
                <p className="text-[15px] font-medium text-foreground">{name || "Your app"} can remember you</p>
                <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
                  {name || "Your app"} can save helpful memories so future
                  conversations feel more continuous.
                </p>
                <p className="mt-3 text-xs font-medium text-foreground/80">
                  Your memories belong to you, not {name || "the app"}.
                </p>
                <div className="mt-4 flex gap-2">
                  <Button size="sm" variant="outline">Not now</Button>
                  <Button size="sm">Turn on</Button>
                </div>
                <div className="mt-5 border-t pt-3">
                  {showPoweredBy ? (
                    <PoweredByMemoryPassport align="start" />
                  ) : (
                    <p className="text-[10px] uppercase tracking-wider text-muted-foreground/50">White-labeled</p>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {createdKey ? (
            <Card className="border-amber-500/40 bg-amber-500/5">
              <CardHeader>
                <CardTitle className="text-base">Save this API key now</CardTitle>
                <CardDescription>
                  This secret is shown once. Store it before continuing.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center gap-2">
                  <code className="min-w-0 flex-1 overflow-x-auto rounded-md bg-neutral-950 px-3 py-2 font-mono text-xs text-neutral-100">
                    {createdKey}
                  </code>
                  <Button variant="outline" size="icon-sm" onClick={copyCreatedKey} aria-label="Copy new API key">
                    <Copy className="size-3.5" />
                  </Button>
                </div>
                <Button className="w-full" onClick={() => router.push("/console/quickstart")}>
                  Continue to quickstart
                  <ArrowRight className="size-4" />
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="flex gap-2">
              <Button variant="outline" className="flex-1" onClick={() => router.back()} disabled={creating}>
                Cancel
              </Button>
              <Button
                className="flex-1"
                disabled={!canCreate || creating}
                onClick={handleCreate}
              >
                {creating ? <Loader2 className="size-4 animate-spin" /> : null}
                {creating ? "Creating..." : "Create app"}
                {!creating && <ArrowRight className="size-4" />}
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
