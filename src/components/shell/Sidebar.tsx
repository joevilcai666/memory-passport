"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Boxes,
  Brain,
  Cpu,
  Settings,
  Rocket,
  Users,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Logo } from "@/components/brand/StampMark";

interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  exact?: boolean;
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

const navGroups: NavGroup[] = [
  {
    label: "Start",
    items: [
      { label: "Overview", href: "/console", icon: LayoutDashboard, exact: true },
      { label: "Get started", href: "/console/quickstart", icon: Rocket },
    ],
  },
  {
    label: "Build",
    items: [
      { label: "Apps", href: "/console/apps", icon: Boxes, exact: true },
      { label: "Policy", href: "/console/memory/policy", icon: Brain },
      { label: "Users", href: "/console/memory/users", icon: Users },
    ],
  },
  {
    label: "Operate",
    items: [
      { label: "Devices", href: "/console/devices", icon: Cpu },
      { label: "Settings", href: "/console/settings", icon: Settings },
    ],
  },
];

function isActive(pathname: string, href: string, exact?: boolean) {
  if (exact) return pathname === href;
  return pathname === href || pathname.startsWith(href + "/");
}

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <aside className="flex h-full w-full flex-col bg-sidebar text-sidebar-foreground">
      {/* Brand */}
      <div className="flex h-16 items-center px-5 border-b border-sidebar-border">
        <Link href="/" onClick={onNavigate} className="transition-opacity hover:opacity-80">
          <Logo />
        </Link>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto ds-scroll px-3 py-4">
        {navGroups.map((group) => (
          <div key={group.label} className="mb-5">
            <div className="px-3 mb-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground/70">
              {group.label}
            </div>
            <ul className="space-y-0.5">
              {group.items.map((item) => {
                const active = isActive(pathname, item.href, item.exact);
                const Icon = item.icon;
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      onClick={onNavigate}
                      className={cn(
                        "group flex h-9 items-center gap-2.5 rounded-md px-3 text-sm font-medium transition-colors",
                        active
                          ? "bg-sidebar-accent text-sidebar-accent-foreground"
                          : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground",
                      )}
                    >
                      <Icon
                        className={cn(
                          "size-4 shrink-0",
                          active ? "text-primary" : "text-muted-foreground/80 group-hover:text-sidebar-accent-foreground",
                        )}
                        strokeWidth={1.5}
                      />
                      <span className="truncate">{item.label}</span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="border-t border-sidebar-border px-4 py-3">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="size-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="tabular">Sandbox · operational</span>
        </div>
      </div>
    </aside>
  );
}
