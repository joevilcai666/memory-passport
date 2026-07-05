import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * StampMark — the Memory Passport brand mark.
 * A circular passport stamp with a stylized "M" formed by a memory/connection motif.
 * Uses currentColor so it inherits text color; pass `className` for sizing.
 */
export function StampMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 32 32"
      fill="none"
      className={cn("size-8", className)}
      aria-hidden="true"
    >
      {/* Outer ring (stamp edge) */}
      <circle
        cx="16"
        cy="16"
        r="14"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeDasharray="1.5 1.8"
        opacity="0.55"
      />
      {/* Inner ring */}
      <circle cx="16" cy="16" r="10" stroke="currentColor" strokeWidth="1.5" opacity="0.9" />
      {/* The M — two peaks forming a memory waveform */}
      <path
        d="M10.5 20.5 L10.5 12.5 L13.5 16 L16 12.5 L18.5 16 L21.5 12.5 L21.5 20.5"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      {/* Base bar — the "passport" baseline */}
      <path d="M9 22.5 L23 22.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" opacity="0.7" />
    </svg>
  );
}

/**
 * The full wordmark — stamp + "Memory Passport" lockup.
 */
export function Logo({
  className,
  showText = true,
  textClassName,
}: {
  className?: string;
  showText?: boolean;
  textClassName?: string;
}) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <StampMark className="size-7 text-primary" />
      {showText && (
        <span className={cn("font-semibold tracking-tight text-[15px] leading-none", textClassName)}>
          Memory&nbsp;Passport
        </span>
      )}
    </span>
  );
}
