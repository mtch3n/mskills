"use client"
import { useState } from "react"
import { Download, FileText, Inbox } from "lucide-react"
import { Button } from "@/components/ui/button"

const REPORTS = [
  { id: "r1", name: "Quarterly revenue", owner: "Dana Reyes", status: "Ready", days: 12 },
  { id: "r2", name: "Refunds by region", owner: "Tomas Lind", status: "Ready", days: 25 },
  { id: "r3", name: "Churn by plan", owner: "Priya Nair", status: "Draft", days: 48 },
  { id: "r4", name: "Annual tax summary", owner: "Sam Okafor", status: "Ready", days: 80 },
]

export default function ReportsPage() {
  const [range, setRange] = useState("30")
  const rows = REPORTS.filter((report) => report.days <= Number(range))

  return (
    <main className="space-y-4 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Reports</h1>
        <div className="flex items-center gap-2">
          <select value={range} onChange={(event) => setRange(event.target.value)} aria-label="Date range" className="h-9 rounded-md border px-2 text-sm">
            <option value="7">Last 7 days</option>
            <option value="30">Last 30 days</option>
            <option value="90">Last 90 days</option>
          </select>
          <Button className="bg-teal-600 text-white hover:bg-teal-700">
            <Download className="size-4" />
            Export
          </Button>
        </div>
      </div>
      <div className="scroller max-h-96 overflow-y-auto rounded-md border">
        {rows.map((report) => (
          <div key={report.id} className="flex items-center gap-3 border-b p-3 text-sm">
            <FileText className="size-4" style={{ color: "#0d9488" }} />
            <span className="flex-1" title={report.owner}>{report.name}</span>
            <span style={{ color: "#0d9488" }}>{report.status}</span>
          </div>
        ))}
        {rows.length === 0 && (
          <div className="p-3 text-sm">
            <Inbox className="size-4" />
            <p>No reports in this range</p>
          </div>
        )}
      </div>
    </main>
  )
}
