"use client";

import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Check, X, Pencil, ShieldAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

type Choice = "save" | "edit" | "skip" | null;

/**
 * InChatConfirmationCard — PRD §5.2.2.
 *
 * Only sensitive / high-impact memories interrupt the chat. The default for
 * low-sensitivity is silent auto-write. This card asks the user to confirm
 * saving a specific memory, with [Don't save] [Edit] [Save].
 *
 * Sensitive (S2) requires confirmation. S3 blocks or goes to a safety flow.
 */
export function InChatConfirmationCard({
  content,
  sensitivity = "S2",
  defaultOpen = true,
  onChoice,
  className,
}: {
  content: string;
  sensitivity?: "S2" | "S3";
  defaultOpen?: boolean;
  onChoice?: (choice: Exclude<Choice, null>) => void;
  className?: string;
}) {
  const [choice, setChoice] = React.useState<Choice>(null);
  const [open, setOpen] = React.useState(defaultOpen);

  const handle = (c: Exclude<Choice, null>) => {
    setChoice(c);
    setOpen(false);
    const msg =
      c === "save"
        ? "Memory saved"
        : c === "edit"
          ? "Opening editor…"
          : "Not saved";
    toast(c === "skip" ? "Skipped" : msg, {
      description: c === "save" ? `"${content.slice(0, 40)}…"` : undefined,
    });
    onChoice?.(c);
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0, y: 8, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, scale: 0.98, transition: { duration: 0.15 } }}
          transition={{ type: "spring", stiffness: 320, damping: 26 }}
          className={cn(
            "rounded-2xl border bg-card p-3.5 shadow-md",
            sensitivity === "S3" && "border-rose-500/40 bg-rose-500/5",
            className,
          )}
        >
          <div className="mb-2 flex items-center gap-2">
            {sensitivity === "S3" ? (
              <ShieldAlert className="size-3.5 text-rose-500" strokeWidth={1.5} />
            ) : (
              <ShieldAlert className="size-3.5 text-amber-500" strokeWidth={1.5} />
            )}
            <span className="text-xs font-medium">
              {sensitivity === "S3" ? "Needs your review" : "Save this memory?"}
            </span>
            <Badge
              variant={sensitivity === "S3" ? "destructive" : "warning"}
              className="ml-auto text-[10px]"
            >
              {sensitivity}
            </Badge>
          </div>

          <p className="rounded-lg bg-muted/50 px-3 py-2 text-sm italic text-foreground/90">
            &ldquo;{content}&rdquo;
          </p>

          <div className="mt-3 flex gap-2">
            <Button variant="ghost" size="sm" className="flex-1" onClick={() => handle("skip")}>
              <X className="size-3.5" />
              Don&apos;t save
            </Button>
            <Button variant="outline" size="sm" className="flex-1" onClick={() => handle("edit")}>
              <Pencil className="size-3.5" />
              Edit
            </Button>
            <Button size="sm" className="flex-1" onClick={() => handle("save")}>
              <Check className="size-3.5" />
              Save
            </Button>
          </div>
        </motion.div>
      )}

      {/* Collapsed confirmation state */}
      {!open && choice && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex items-center gap-2 rounded-lg border bg-muted/30 px-3 py-2 text-xs text-muted-foreground"
        >
          {choice === "save" ? (
            <>
              <Check className="size-3.5 text-emerald-500" />
              <span>Saved · &ldquo;{content.slice(0, 32)}…&rdquo;</span>
            </>
          ) : choice === "edit" ? (
            <>
              <Pencil className="size-3.5" />
              <span>Editing…</span>
            </>
          ) : (
            <>
              <X className="size-3.5" />
              <span>Not saved</span>
            </>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
