"use client";

import Link from "next/link";
import { Plus, ArrowRight, Bot, Cpu, Layers } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useMemoryStore } from "@/store/memory-store";
import { formatRelativeDay } from "@/lib/utils";
import type { ProductType } from "@/lib/types";

const productTypeIcon: Record<ProductType, typeof Bot> = {
  software: Bot,
  hardware: Cpu,
  hybrid: Layers,
};

const productTypeLabel: Record<ProductType, string> = {
  software: "Software companion",
  hardware: "Robot hardware",
  hybrid: "Hybrid",
};

export default function AppsPage() {
  const app = useMemoryStore((s) => s.app);
  const Icon = productTypeIcon[app.product_type];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-medium tracking-tight">Apps</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            Each app is one product surface that embeds Memory Passport.
          </p>
        </div>
        <Button asChild>
          <Link href="/console/apps/new">
            <Plus className="size-4" />
            New app
          </Link>
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="transition-colors hover:border-primary/40">
          <Link href={`/console/apps/${app.id}`} className="block">
            <CardContent className="flex items-start gap-4">
              <div className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-primary/10">
                <Icon className="size-5 text-primary" strokeWidth={1.5} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold">{app.name}</h3>
                  <Badge variant="success" className="gap-1 text-[10px]">
                    <span className="size-1.5 rounded-full bg-emerald-500" />
                    {app.status}
                  </Badge>
                </div>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {productTypeLabel[app.product_type]} · {app.data_region}
                </p>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <Badge variant="secondary" className="font-mono text-[10px]">{app.id}</Badge>
                  <Badge variant="outline" className="text-[10px] capitalize">{app.environment}</Badge>
                  {app.show_powered_by ? (
                    <Badge variant="ink" className="text-[10px]">Powered by visible</Badge>
                  ) : (
                    <Badge variant="outline" className="text-[10px]">White-label</Badge>
                  )}
                </div>
                <p className="mt-3 text-[11px] text-muted-foreground/70">
                  Created {formatRelativeDay(app.created_at)} · {app.api_keys.length} API keys
                </p>
              </div>
              <ArrowRight className="size-4 shrink-0 text-muted-foreground/50" />
            </CardContent>
          </Link>
        </Card>

        {/* Create new card */}
        <Card className="border-dashed">
          <Link href="/console/apps/new" className="block h-full">
            <CardContent className="flex h-full min-h-[140px] flex-col items-center justify-center gap-2 text-center">
              <div className="flex size-10 items-center justify-center rounded-xl bg-muted">
                <Plus className="size-5 text-muted-foreground" strokeWidth={1.5} />
              </div>
              <p className="text-sm font-medium">Create a new app</p>
              <p className="text-xs text-muted-foreground">For another product or environment</p>
            </CardContent>
          </Link>
        </Card>
      </div>
    </div>
  );
}
