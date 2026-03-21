"use client"

import { useRouter } from "next/navigation"
import { AlertTriangle, Plus, Bell } from "lucide-react"
import { AlertCard } from "./alert-card"

const sampleAlerts = [
  {
    id: 1,
    title: "Suspicious activity reported near Main Library",
    location: "Alderman Library",
    time: "5 min ago",
    severity: "high" as const,
  },
  {
    id: 2,
    title: "Weather advisory: Heavy rain expected",
    location: "Campus-wide",
    time: "15 min ago",
    severity: "medium" as const,
  },
  {
    id: 3,
    title: "Building maintenance in progress",
    location: "Engineering Hall",
    time: "1 hour ago",
    severity: "low" as const,
  },
  {
    id: 4,
    title: "Traffic disruption on University Ave",
    location: "University Avenue",
    time: "2 hours ago",
    severity: "medium" as const,
  },
  {
    id: 5,
    title: "Fire drill scheduled for tomorrow",
    location: "Newcomb Hall",
    time: "3 hours ago",
    severity: "low" as const,
  },
]

export function Sidebar() {
  const router = useRouter()

  return (
    <aside className="h-full flex flex-col bg-card rounded-2xl border border-border shadow-sm overflow-hidden">
      
      {/* Report Incident Button */}
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

      {/* Alerts Panel */}
      <div className="flex-1 flex flex-col min-h-0 px-5 pb-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Bell className="w-5 h-5 text-primary" />
            <h2 className="font-semibold text-foreground">Recent Alerts</h2>
          </div>
          <span className="text-xs text-muted-foreground bg-secondary px-2 py-1 rounded-full">
            {sampleAlerts.length} new
          </span>
        </div>

        {/* Scrollable alerts list */}
        <div className="flex-1 overflow-y-auto space-y-3 pr-1 -mr-1">
          {sampleAlerts.map((alert) => (
            <AlertCard
              key={alert.id}
              title={alert.title}
              location={alert.location}
              time={alert.time}
              severity={alert.severity}
            />
          ))}
        </div>

        {/* View all link */}
        <div className="pt-4 mt-4 border-t border-border">
          <button className="w-full text-sm text-primary hover:text-primary/80 font-medium transition-colors">
            View all alerts →
          </button>
        </div>
      </div>
    </aside>
  )
}