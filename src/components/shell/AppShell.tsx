"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PoweredByMemoryPassport } from "@/components/brand/PoweredByMemoryPassport";
import { cn } from "@/lib/utils";

/**
 * AppShell — the embedded consumer surface (i.e. inside the "Luna" companion app).
 *
 * This is the warm "paper" side of the Ink & Paper system. By default it forces
 * the light-paper surface via `.paper-surface`, regardless of the site theme —
 * so the consumer experience always feels warm and trustworthy.
 *
 * Layout: a centered phone-width column (max-w-md) with an optional app-style
 * top bar showing a back link, a title, and an overflow menu. The
 * PoweredByMemoryPassport watermark anchors the footer on every screen.
 */
export function AppShell({
  children,
  title,
  backHref,
  showWatermark = true,
  actions,
  headerCenter,
  className,
}: {
  children: React.ReactNode;
  title?: string;
  backHref?: string;
  showWatermark?: boolean;
  actions?: React.ReactNode;
  headerCenter?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className="paper-surface min-h-dvh bg-background text-foreground">
      <div className="mx-auto flex min-h-dvh w-full max-w-md flex-col">
        {/* App-style header */}
        <header className="sticky top-0 z-30 flex h-14 items-center gap-2 border-b border-border/60 bg-background/85 px-3 backdrop-blur-md">
          {backHref && (
            <Button variant="ghost" size="icon-sm" asChild>
              <Link href={backHref} aria-label="Back">
                <ArrowLeft className="size-4" />
              </Link>
            </Button>
          )}
          <div className="flex-1 truncate text-center text-[15px] font-medium">
            {headerCenter ?? title}
          </div>
          {actions ?? <div className="size-8" />}
        </header>

        {/* Body */}
        <main className={cn("flex-1 px-5 py-6", className)}>{children}</main>

        {/* Watermark footer */}
        {showWatermark && (
          <footer className="px-5 py-5">
            <PoweredByMemoryPassport />
          </footer>
        )}
      </div>
    </div>
  );
}
