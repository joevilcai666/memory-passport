import * as React from "react"

import { cn } from "@/lib/utils"

function Kbd({ className, ...props }: React.ComponentProps<"kbd">) {
  return (
    <kbd
      data-slot="kbd"
      className={cn(
        "pointer-events-none h-5 select-none rounded border bg-muted px-1.5 font-mono text-xs text-muted-foreground",
        className
      )}
      {...props}
    />
  )
}

export { Kbd }
