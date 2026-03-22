"use client";

import { useMemo } from "react";
import { Circle, MapContainer, Popup, TileLayer } from "react-leaflet";
import "leaflet/dist/leaflet.css";

export type MapReport = {
  id: string;
  position: [number, number];
  type: string;
  location: string;
  severity: number;
  riskLabel: string;
  confidence: number | null;
  updatedAt?: string | null;
};

function circleColor(severity: number): string {
  // Keep map colors aligned with sidebar alert buckets:
  // high (>=4), medium (=3), low (<=2)
  if (severity >= 4) return "#DC2626"; // red
  if (severity >= 3) return "#F97316"; // orange
  return "#EAB308"; // yellow
}

type Props = {
  reports: MapReport[];
};

export default function IncidentLiveMap({ reports }: Props) {
  const displayReports = useMemo(() => {
    const grouped = new Map<string, MapReport[]>();
    for (const report of reports) {
      if (!Array.isArray(report.position) || report.position.length < 2) continue;
      const [latitude, longitude] = report.position;
      if (typeof latitude !== "number" || typeof longitude !== "number") continue;
      if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) continue;

      const key = `${latitude.toFixed(6)},${longitude.toFixed(6)}`;
      const existing = grouped.get(key);
      if (existing) {
        existing.push(report);
      } else {
        grouped.set(key, [report]);
      }
    }

    const positioned: Array<{ report: MapReport; position: [number, number] }> = [];
    for (const group of grouped.values()) {
      if (group.length === 1) {
        positioned.push({ report: group[0], position: group[0].position });
        continue;
      }

      group.forEach((report, idx) => {
        const [baseLat, baseLng] = report.position;
        const angle = (2 * Math.PI * idx) / group.length;
        const offsetLat = 0.00018 * Math.cos(angle);
        const offsetLng = (0.00018 * Math.sin(angle)) / Math.max(Math.cos((baseLat * Math.PI) / 180), 0.2);
        positioned.push({
          report,
          position: [baseLat + offsetLat, baseLng + offsetLng],
        });
      });
    }

    return positioned;
  }, [reports]);

  return (
    <MapContainer
      center={[38.0336, -78.508]}
      zoom={15}
      minZoom={14}
      maxZoom={19}
      maxBounds={[
        [38.0, -78.55],
        [38.07, -78.45],
      ]}
      maxBoundsViscosity={1.0}
      scrollWheelZoom={true}
      className="h-full w-full rounded-xl shadow-lg border"
    >
      <TileLayer
        attribution="&copy; OpenStreetMap contributors"
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {displayReports.map(({ report, position }) => (
        <Circle
          key={report.id}
          center={position}
          radius={40}
          pathOptions={{
            color: circleColor(report.severity),
            fillColor: circleColor(report.severity),
            fillOpacity: 0.28,
          }}
        >
          <Popup>
            <div className="text-sm">
              <div className="font-semibold">{report.type}</div>
              <div>{report.location}</div>
              <div>Severity: {report.severity}</div>
              <div>Risk: {report.riskLabel}</div>
              <div>
                Confidence:{" "}
                {typeof report.confidence === "number"
                  ? `${Math.round(report.confidence * 100)}%`
                  : "n/a"}
              </div>
            </div>
          </Popup>
        </Circle>
      ))}
    </MapContainer>
  );
}
