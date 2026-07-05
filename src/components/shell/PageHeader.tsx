import * as React from "react";
import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

export interface PageHeaderProps {
  title?: string;
  description?: string;
  actions?: React.ReactNode;
  breadcrumb?: { label: string; href?: string }[];
}

export function PageHeader({ title, description, actions, breadcrumb }: PageHeaderProps) {
  if (!title && !actions) return null;
  return (
    <div className="sticky top-16 z-20 flex items-center gap-4 border-b bg-background/80 px-4 py-4 backdrop-blur-md md:px-6">
      <div className="min-w-0 flex-1">
        {breadcrumb && breadcrumb.length > 0 && (
          <nav className="mb-1 flex items-center gap-1 text-xs text-muted-foreground">
            {breadcrumb.map((b, i) => (
              <React.Fragment key={i}>
                {b.href ? (
                  <Link href={b.href} className="hover:text-foreground transition-colors">
                    {b.label}
                  </Link>
                ) : (
                  <span>{b.label}</span>
                )}
                {i < breadcrumb.length - 1 && (
                  <ChevronRight className="size-3 opacity-50" />
                )}
              </React.Fragment>
            ))}
          </nav>
        )}
        {title && (
          <h1 className="truncate text-xl font-medium tracking-tight text-accent-foreground md:text-2xl">
            {title}
          </h1>
        )}
        {description && (
          <p className="mt-0.5 text-sm text-muted-foreground">{description}</p>
        )}
      </div>
      {actions && <div className={cn("flex shrink-0 items-center gap-2")}>{actions}</div>}
    </div>
  );
}
