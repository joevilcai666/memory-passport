import * as React from "react";

/**
 * The embedded user UI (inside "Luna"). Forces the light "paper" surface
 * regardless of the site theme, so the consumer experience is always warm.
 */
export default function AppGroupLayout({ children }: { children: React.ReactNode }) {
  // Force light theme for this route group via a wrapper class.
  // The ThemeProvider sets `class="dark"` on <html>; here we override per-subtree
  // by NOT relying on .dark — AppShell uses .paper-surface which redefines tokens.
  return <>{children}</>;
}
