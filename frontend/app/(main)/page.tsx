"use client";

import { Header } from "@/components/header";
import { Sidebar } from "@/components/sidebar";
import { MapContainer, TileLayer, Marker, Popup, Circle} from "react-leaflet";
import "leaflet/dist/leaflet.css";

export default function HoosAlertPage() {

  const reports = [
    {
      id: 1,
      position: [38.0336, -78.5080],
      type: "Theft",
    },
    {
      id: 2,
      position: [38.0357, -78.5034],
      type: "Suspicious Activity",
    },
  ]
  return (
    <div className="h-screen flex flex-col bg-background pt-6">

      {/* Main */}
      <main className="h-[80%] flex gap-5 p-5 pt-0">
        
        {/* Map */}
        <div className="w-3/4 h-full">
          <div className="h-full w-full">
            <MapContainer
            center={[38.0336, -78.5080]}
            zoom={15}
            minZoom={14}   // can't zoom out too far
            maxZoom={19}   // optional: limit zoom in
            maxBounds={[
              [38.00, -78.55],  // southwest corner
              [38.07, -78.45],  // northeast corner
            ]}
            maxBoundsViscosity={1.0} // prevents dragging outside bounds
            scrollWheelZoom={true}
            className="h-full w-full rounded-xl shadow-lg border"
            >

              <TileLayer
                attribution='&copy; OpenStreetMap contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
                {/* 🔴 ADD THIS BLOCK RIGHT HERE */}
  {reports.map((report) => (
    <Circle
      key={report.id}
      center={report.position}
      radius={30}
      pathOptions={{
        color: "red",
        fillColor: "red",
        fillOpacity: 0.3,
      }}
    />
  ))}
            </MapContainer>
          </div>
        </div>

        {/* Sidebar */}
        <div className="w-1/4 h-full">
          <Sidebar />
        </div>

      </main>
    </div>
  );
}