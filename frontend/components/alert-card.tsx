import { AlertTriangle, Clock, MapPin } from "lucide-react"

interface AlertCardProps {
  title: string
  location: string
  time: string
  severity: "high" | "medium" | "low"
}

export function AlertCard({ title, location, time, severity }: AlertCardProps) {
  const severityStyles = {
    high: "border-l-destructive bg-destructive/5",
    medium: "border-l-orange-500 bg-orange-50",
    low: "border-l-yellow-500 bg-yellow-50",
  }

  const severityBadge = {
    high: "bg-destructive/10 text-destructive",
    medium: "bg-orange-100 text-orange-700",
    low: "bg-yellow-100 text-yellow-700",
  }

  return (
    <div
      className={`p-4 rounded-xl border border-border border-l-4 ${severityStyles[severity]} transition-all duration-200 hover:shadow-md hover:scale-[1.02] cursor-pointer`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <span
              className={`text-xs font-medium px-2 py-0.5 rounded-full ${severityBadge[severity]}`}
            >
              {severity.charAt(0).toUpperCase() + severity.slice(1)}
            </span>
          </div>
          <h3 className="font-medium text-foreground text-sm leading-tight mb-2 line-clamp-2">
            {title}
          </h3>
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <MapPin className="w-3 h-3 shrink-0" />
              <span className="truncate">{location}</span>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Clock className="w-3 h-3 shrink-0" />
              <span>{time}</span>
            </div>
          </div>
        </div>
        <AlertTriangle
          className={`w-5 h-5 shrink-0 ${
            severity === "high"
              ? "text-destructive"
              : severity === "medium"
              ? "text-orange-500"
              : "text-yellow-500"
          }`}
        />
      </div>
    </div>
  )
}
