"use client"

import { useRouter } from "next/navigation"
import { AlertTriangle, Plus, Bell } from "lucide-react"
import { AlertCard } from "./alert-card"
import type { MapReport } from "./incident-live-map"

type Props = {
  reports: MapReport[]
}

function toAlertSeverity(severity: number): "high" | "medium" | "low" {
  if (severity >= 4) return "high"
  if (severity >= 3) return "medium"
  return "low"
}

function formatRelativeTime(updatedAt?: string | null): string {
  if (!updatedAt) return "just now"

  const timestamp = new Date(updatedAt).getTime()
  if (!Number.isFinite(timestamp)) return "just now"

  const deltaSeconds = Math.max(0, Math.floor((Date.now() - timestamp) / 1000))
  if (deltaSeconds < 60) return "just now"
  if (deltaSeconds < 3600) return `${Math.floor(deltaSeconds / 60)} min ago`
  if (deltaSeconds < 86400) return `${Math.floor(deltaSeconds / 3600)} hr ago`

  const days = Math.floor(deltaSeconds / 86400)
  return `${days} day${days === 1 ? "" : "s"} ago`
}

export function Sidebar({ reports }: Props) {
  const router = useRouter()

  return (
    <aside className="h-full flex flex-col bg-card rounded-2xl border border-border shadow-sm overflow-hidden">
      <div className="p-5">
        <button
          onClick={() => router.push("/report")}
          className="w-full flex items-center justify-center gap-3 bg-destructive hover:bg-destructive/90 text-destructive-foreground font-semibold py-4 px-6 rounded-xl transition-all duration-200 shadow-lg hover:shadow-xl hover:scale-[1.02] active:scale-[0.98]"
        >
          <AlertTriangle className="w-5 h-5" />
          <span>Report Incident</span>
          <Plus className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 flex flex-col min-h-0 px-5 pb-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Bell className="w-5 h-5 text-primary" />
            <h2 className="font-semibold text-foreground">Recent Alerts</h2>
          </div>
          <span className="text-xs text-muted-foreground bg-secondary px-2 py-1 rounded-full">
            {reports.length} live
          </span>
        </div>

        <div className="flex-1 overflow-y-auto space-y-3 pr-1 -mr-1">
          {reports.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border p-4 text-sm text-muted-foreground">
              No live reports yet.
            </div>
          ) : (
            reports.map((report) => (
              <AlertCard
                key={report.id}
                title={report.type}
                location={report.location}
                time={formatRelativeTime(report.updatedAt)}
                severity={toAlertSeverity(report.severity)}
              />
            ))
          )}
        </div>
      </div>
    </aside>
  )
}
