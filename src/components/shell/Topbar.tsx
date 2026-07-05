"use client";

import * as React from "react";
import Link from "next/link";
import { useTheme } from "next-themes";
import { Sun, Moon, Menu, ExternalLink, Smartphone, Brain, ShieldCheck, ArrowLeftRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";

/** Hydration-safe mounted flag without calling setState inside an effect. */
function useMounted() {
  return React.useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  );
}

function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const mounted = useMounted();
  if (!mounted) return <div className="size-8" />;
  const isDark = theme === "dark";
  return (
    <Button
      variant="ghost"
     size="icon-sm"
      onClick={() => setTheme(isDark ? "light" : "dark")}
      aria-label="Toggle theme"
    >
      {isDark ? <Sun className="size-4" /> : <Moon className="size-4" />}
    </Button>
  );
}

export function Topbar({ onMenuClick }: { onMenuClick?: () => void }) {
  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b bg-background/80 px-4 backdrop-blur-md md:px-6">
      <Button
        variant="ghost"
        size="icon-sm"
        className="lg:hidden"
        onClick={onMenuClick}
        aria-label="Open navigation"
      >
        <Menu className="size-4" />
      </Button>

      <div className="flex-1" />

      {/* Preview as user — the Stripe "view as customer" pattern.
          Always-visible doorway into the embedded user UI (the wedge demo
          lives here: migration, consent, memory center). */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="sm" className="gap-1.5">
            <Smartphone className="size-3.5" />
            <span className="hidden sm:inline">Preview as user</span>
            <span className="sm:hidden">Preview</span>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-60">
          <DropdownMenuLabel className="text-xs text-muted-foreground">
            See what your users see
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem asChild>
            <Link href="/app/memory" className="flex items-center gap-2">
              <Brain className="size-3.5" /> Memory Center
            </Link>
          </DropdownMenuItem>
          <DropdownMenuItem asChild>
            <Link href="/app/consent" className="flex items-center gap-2">
              <ShieldCheck className="size-3.5" /> Consent screen
            </Link>
          </DropdownMenuItem>
          <DropdownMenuItem asChild>
            <Link href="/app/devices/bind" className="flex items-center gap-2">
              <Smartphone className="size-3.5" /> Device binding
            </Link>
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem asChild>
            <Link href="/app/migrate" className="flex items-center gap-2">
              <ArrowLeftRight className="size-3.5 text-primary" />
              <span className="font-medium text-primary">Migration demo</span>
              <Badge variant="ink" className="ml-auto text-[9px]">wedge</Badge>
            </Link>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Sandbox/Prod env switcher */}
      <EnvSwitcher />

      <ThemeToggle />

      {/* Account */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button className="flex items-center gap-2 rounded-full outline-none focus-visible:ring-2 focus-visible:ring-ring">
            <Avatar className="size-8 border">
              <AvatarFallback className="bg-primary text-primary-foreground text-xs font-semibold">
                MC
              </AvatarFallback>
            </Avatar>
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56">
          <DropdownMenuLabel className="flex flex-col gap-0.5">
            <span className="text-sm font-medium">Mia Chen</span>
            <span className="text-xs font-normal text-muted-foreground">mia@luna.inc</span>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">Role</span>
            <Badge variant="secondary" className="text-[10px]">Owner</Badge>
          </DropdownMenuItem>
          <DropdownMenuItem asChild>
            <Link href="/console/settings">Settings</Link>
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem className="text-muted-foreground">
            <Link href="/" className="flex items-center gap-2">
              Sign out
            </Link>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  );
}

function EnvSwitcher() {
  const [env, setEnv] = React.useState<"sandbox" | "production">("sandbox");
  return (
    <div className="flex items-center rounded-md border bg-muted/50 p-0.5">
      {(["sandbox", "production"] as const).map((e) => (
        <button
          key={e}
          onClick={() => setEnv(e)}
          className={cn(
            "rounded-sm px-2.5 py-1 text-xs font-medium capitalize transition-colors",
            env === e
              ? "bg-background text-foreground shadow-xs"
              : "text-muted-foreground hover:text-foreground",
          )}
        >
          {e === "production" ? "Prod" : "Sandbox"}
        </button>
      ))}
    </div>
  );
}
