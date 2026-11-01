"use client"
import * as React from "react"
import { DayPicker } from "react-day-picker"
import { cn } from "@/lib/utils"

function Calendar({ className, showOutsideDays = true, ...props }: React.ComponentProps<typeof DayPicker>) {
  return <DayPicker data-slot="calendar" showOutsideDays={showOutsideDays} className={cn("p-3", className)} {...props} />
}

export { Calendar }
