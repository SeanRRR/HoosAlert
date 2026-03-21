import { MapPin, ZoomIn, ZoomOut, Locate, Layers } from "lucide-react"

export function MapView() {
  return (
    <div className="h-full relative bg-card rounded-2xl border border-border overflow-hidden shadow-sm">
      {/* Map Placeholder */}
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-background to-primary/10">
        <div className="absolute inset-0 opacity-20">
          {/* Grid pattern */}
          <div
            className="w-full h-full"
            style={{
              backgroundImage: `
                linear-gradient(to right, var(--border) 1px, transparent 1px),
                linear-gradient(to bottom, var(--border) 1px, transparent 1px)
              `,
              backgroundSize: "40px 40px",
            }}
          />
        </div>

        {/* Sample location markers */}
        <div className="absolute top-1/3 left-1/4 w-3 h-3 bg-primary rounded-full animate-pulse shadow-lg" />
        <div className="absolute top-1/2 left-1/2 w-4 h-4 bg-destructive rounded-full animate-pulse shadow-lg" />
        <div className="absolute top-2/3 left-3/4 w-3 h-3 bg-primary rounded-full animate-pulse shadow-lg" />
        <div className="absolute top-1/4 left-2/3 w-3 h-3 bg-primary/70 rounded-full shadow-lg" />

        {/* Center indicator */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="flex flex-col items-center gap-2">
            <MapPin className="w-12 h-12 text-primary drop-shadow-md" />
            <span className="text-sm font-medium text-foreground bg-card/90 px-4 py-2 rounded-full shadow-sm border border-border">
              Map View
            </span>
          </div>
        </div>
      </div>

      {/* Map controls */}
      <div className="absolute right-4 top-4 flex flex-col gap-2">
        <button className="w-10 h-10 bg-card rounded-xl border border-border shadow-sm flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-accent transition-colors">
          <ZoomIn className="w-5 h-5" />
        </button>
        <button className="w-10 h-10 bg-card rounded-xl border border-border shadow-sm flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-accent transition-colors">
          <ZoomOut className="w-5 h-5" />
        </button>
        <button className="w-10 h-10 bg-card rounded-xl border border-border shadow-sm flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-accent transition-colors">
          <Locate className="w-5 h-5" />
        </button>
        <button className="w-10 h-10 bg-card rounded-xl border border-border shadow-sm flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-accent transition-colors">
          <Layers className="w-5 h-5" />
        </button>
      </div>

      {/* Scale indicator */}
      <div className="absolute bottom-4 left-4 bg-card/90 px-3 py-1.5 rounded-lg border border-border text-xs text-muted-foreground shadow-sm">
        <div className="flex items-center gap-2">
          <div className="w-12 h-0.5 bg-muted-foreground rounded-full" />
          <span>500m</span>
        </div>
      </div>
    </div>
  )
}
