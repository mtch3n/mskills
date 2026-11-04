import * as React from "react"
import { cn } from "@/lib/utils"

function Empty({ className, ...props }: React.ComponentProps<"div">) {
  return <div data-slot="empty" className={cn("flex flex-col items-center justify-center gap-2 p-8 text-center", className)} {...props} />
}

function EmptyMedia({ className, ...props }: React.ComponentProps<"div">) {
  return <div data-slot="empty-media" className={cn("text-muted-foreground", className)} {...props} />
}

function EmptyTitle({ className, ...props }: React.ComponentProps<"div">) {
  return <div data-slot="empty-title" className={cn("text-sm font-medium", className)} {...props} />
}

export { Empty, EmptyMedia, EmptyTitle }
