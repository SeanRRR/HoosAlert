"use client";

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
  if (severity >= 5) return "#B91C1C";
  if (severity >= 4) return "#DC2626";
  if (severity >= 3) return "#F97316";
  if (severity >= 2) return "#EAB308";
  return "#22C55E";
}

type Props = {
  reports: MapReport[];
};

export default function IncidentLiveMap({ reports }: Props) {
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

      {reports.map((report) => (
        <Circle
          key={report.id}
          center={report.position}
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
