"use client";

import * as React from "react";
import { Copy, Check, Plus, Eye, EyeOff, RotateCcw } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useMemoryStore } from "@/store/memory-store";
import { formatRelativeDay, cn } from "@/lib/utils";
import { toast } from "sonner";

export default function AppDetailPage() {
  const app = useMemoryStore((s) => s.app);
  const [revealed, setRevealed] = React.useState<Record<string, boolean>>({});
  const [copied, setCopied] = React.useState<string | null>(null);

  const copy = (key: string, id: string) => {
    navigator.clipboard?.writeText(key);
    setCopied(id);
    toast.success("API key copied");
    setTimeout(() => setCopied(null), 1500);
  };

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
            <Button size="sm" variant="outline">
              <Plus className="size-3.5" />
              New key
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {app.api_keys.map((k) => {
            const isRevealed = revealed[k.id];
            const display = isRevealed ? k.key : k.key.slice(0, 14) + "••••••••••••••••••";
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
                    {display}
                  </code>
                  <Button
                    variant="outline"
                    size="icon-sm"
                    onClick={() => setRevealed((r) => ({ ...r, [k.id]: !r[k.id] }))}
                    aria-label={isRevealed ? "Hide key" : "Reveal key"}
                  >
                    {isRevealed ? <EyeOff className="size-3.5" /> : <Eye className="size-3.5" />}
                  </Button>
                  <Button
                    variant="outline"
                    size="icon-sm"
                    onClick={() => copy(k.key, k.id)}
                    aria-label="Copy key"
                  >
                    {copied === k.id ? <Check className="size-3.5 text-emerald-500" /> : <Copy className="size-3.5" />}
                  </Button>
                  <Button variant="ghost" size="icon-sm" aria-label="Roll key">
                    <RotateCcw className="size-3.5" />
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
            {[
              { label: "API key", ok: true },
              { label: "Test user", ok: true },
              { label: "First event", ok: true },
              { label: "Retrieve", ok: true },
            ].map((s) => (
              <div key={s.label} className="flex items-center gap-2 rounded-lg border p-3">
                <span className={cn("size-2 rounded-full", s.ok ? "bg-emerald-500" : "bg-muted-foreground/30")} />
                <span className="text-sm">{s.label}</span>
                {s.ok && <Check className="ml-auto size-3.5 text-emerald-500" />}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
