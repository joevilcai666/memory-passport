"use client";

import * as React from "react";
import { Copy, Check, Plus, RotateCcw, Loader2, X } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useMemoryStore } from "@/store/memory-store";
import { formatRelativeDay, cn } from "@/lib/utils";
import { toast } from "sonner";

export default function AppDetailPage() {
  const { app, quickstart, dataMode, createApiKey, rotateApiKey } = useMemoryStore();
  const [copied, setCopied] = React.useState<string | null>(null);
  const [creatingKey, setCreatingKey] = React.useState(false);
  const [rotatingKey, setRotatingKey] = React.useState<string | null>(null);
  const [oneTimeKey, setOneTimeKey] = React.useState<{ id: string; key: string } | null>(null);

  const copy = async (key: string, id: string) => {
    try {
      await navigator.clipboard.writeText(key);
      setCopied(id);
      toast.success("API key copied");
      setTimeout(() => setCopied(null), 1500);
    } catch (error) {
      toast.error("Could not copy API key", {
        description: error instanceof Error ? error.message : "Clipboard unavailable",
      });
    }
  };

  const handleCreateKey = async () => {
    if (creatingKey) return;
    setCreatingKey(true);
    try {
      const created = await createApiKey(app.id, {
        label: "Console key",
        environment: app.environment,
      });
      setOneTimeKey({ id: created.id, key: created.key });
    } catch (error) {
      toast.error("API key creation failed", {
        description: error instanceof Error ? error.message : "Unknown error",
      });
    } finally {
      setCreatingKey(false);
    }
  };

  const handleRotateKey = async (keyId: string) => {
    if (rotatingKey) return;
    setRotatingKey(keyId);
    try {
      const rotated = await rotateApiKey(app.id, keyId);
      setOneTimeKey({ id: rotated.id, key: rotated.key });
    } catch (error) {
      toast.error("API key rotation failed", {
        description: error instanceof Error ? error.message : "Unknown error",
      });
    } finally {
      setRotatingKey(null);
    }
  };

  const integration = [
    { id: "api-key", label: "API key", ok: dataMode === "live" && app.api_keys.length > 0 },
    { id: "test-user", label: "Test user", ok: dataMode === "live" && quickstart.testUserCreated },
    { id: "first-event", label: "First event", ok: dataMode === "live" && quickstart.firstEventSent },
    { id: "retrieve", label: "Retrieve", ok: dataMode === "live" && quickstart.firstRetrieveDone },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-medium tracking-tight">{app.name}</h1>
            <Badge variant="success" className="gap-1">
              <span className="size-1.5 rounded-full bg-emerald-500" />
              {app.status}
            </Badge>
          </div>
          <p className="mt-0.5 text-sm text-muted-foreground">
            <span className="font-mono text-xs">{app.id}</span> · {app.product_type} · {app.data_region}
          </p>
        </div>
      </div>

      {/* API Keys */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>API keys</CardTitle>
              <CardDescription>Use these to initialize the SDK. Keep secret.</CardDescription>
            </div>
            <Button size="sm" variant="outline" onClick={handleCreateKey} disabled={creatingKey || dataMode !== "live"}>
              {creatingKey ? <Loader2 className="size-3.5 animate-spin" /> : <Plus className="size-3.5" />}
              {creatingKey ? "Creating key..." : "New key"}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {oneTimeKey && (
            <div className="rounded-lg border border-amber-500/40 bg-amber-500/5 p-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-medium">One-time API key</p>
                  <p className="text-xs text-muted-foreground">Copy it now. It will be masked after this view.</p>
                </div>
                <Button variant="ghost" size="icon-sm" onClick={() => setOneTimeKey(null)} aria-label="Dismiss API key">
                  <X className="size-3.5" />
                </Button>
              </div>
              <div className="mt-3 flex items-center gap-2">
                <code className="min-w-0 flex-1 overflow-x-auto rounded-md bg-neutral-950 px-3 py-2 font-mono text-xs text-neutral-100">
                  {oneTimeKey.key}
                </code>
                <Button
                  variant="outline"
                  size="icon-sm"
                  onClick={() => copy(oneTimeKey.key, oneTimeKey.id)}
                  aria-label="Copy new API key"
                >
                  {copied === oneTimeKey.id ? <Check className="size-3.5 text-emerald-500" /> : <Copy className="size-3.5" />}
                </Button>
              </div>
            </div>
          )}
          {app.api_keys.map((k) => {
            return (
              <div key={k.id} className="rounded-lg border p-4">
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{k.label}</span>
                      <Badge
                        variant={k.environment === "production" ? "default" : "secondary"}
                        className="text-[10px] capitalize"
                      >
                        {k.environment}
                      </Badge>
                    </div>
                    <p className="mt-1 text-[11px] text-muted-foreground">
                      Created {formatRelativeDay(k.created_at)}
                      {k.last_used_at && ` · last used ${formatRelativeDay(k.last_used_at)}`}
                    </p>
                  </div>
                </div>
                <div className="mt-3 flex items-center gap-2">
                  <code className="flex-1 truncate rounded-md bg-muted px-3 py-2 font-mono text-xs">
                    {k.key}
                  </code>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    aria-label="Roll key"
                    onClick={() => handleRotateKey(k.id)}
                    disabled={rotatingKey !== null || dataMode !== "live"}
                  >
                    {rotatingKey === k.id ? <Loader2 className="size-3.5 animate-spin" /> : <RotateCcw className="size-3.5" />}
                  </Button>
                </div>
              </div>
            );
          })}
        </CardContent>
      </Card>

      {/* Integration status */}
      <Card>
        <CardHeader>
          <CardTitle>Integration</CardTitle>
          <CardDescription>Quick health of the SDK connection.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-4">
            {integration.map((s) => (
              <div key={s.label} data-testid={`integration-${s.id}`} className="flex items-center gap-2 rounded-lg border p-3">
                <span className={cn("size-2 rounded-full", s.ok ? "bg-emerald-500" : "bg-muted-foreground/30")} />
                <span className="text-sm">{s.label}</span>
                <span className="ml-auto text-xs text-muted-foreground">{s.ok ? "Ready" : "Not tested"}</span>
                {s.ok && <Check className="size-3.5 text-emerald-500" />}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
