"use client";

import { Dispatch, SetStateAction } from "react";
import { MapContainer, Marker, TileLayer, useMapEvents } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";

delete (L.Icon.Default.prototype as unknown as { _getIconUrl?: unknown })._getIconUrl;

L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

type Props = {
  selectedPosition: [number, number] | null;
  setSelectedPosition: Dispatch<SetStateAction<[number, number] | null>>;
};

function LocationPicker({
  setSelectedPosition,
}: Pick<Props, "setSelectedPosition">) {
  useMapEvents({
    click(event) {
      setSelectedPosition([event.latlng.lat, event.latlng.lng]);
    },
  });
  return null;
}

export default function ReportLocationMap({
  selectedPosition,
  setSelectedPosition,
}: Props) {
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
      className="h-full w-full"
    >
      <TileLayer
        attribution="&copy; OpenStreetMap"
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <LocationPicker setSelectedPosition={setSelectedPosition} />
      {selectedPosition && <Marker position={selectedPosition} />}
    </MapContainer>
  );
}
