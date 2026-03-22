"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import type { MapReport } from "@/components/incident-live-map";
import { Sidebar } from "@/components/sidebar";

type IncidentPayload = {
  id?: string | number;
  title?: string;
  location?: string;
  latitude?: number | null;
  longitude?: number | null;
  lat?: number | null;
  lng?: number | null;
  severity?: number;
  risk_label?: string;
  score_confidence?: number;
  created_at?: string;
};

type SocketEventPayload = {
  incident?: IncidentPayload;
  score?: {
    confidence?: number;
  };
};

const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");
const WS_URL = `${API_BASE_URL.replace(/^http/i, "ws")}/ws`;
const PENDING_EVENT_KEY = "hoosalert:pending-event";
const IncidentLiveMap = dynamic(() => import("@/components/incident-live-map"), {
  ssr: false,
  loading: () => <div className="h-full w-full rounded-xl border p-4">Loading map...</div>,
});

const initialReports: MapReport[] = [
  {
    id: "seed-1",
    position: [38.0336, -78.508],
    type: "Theft",
    location: "Central Grounds",
    severity: 3,
    riskLabel: "security",
    confidence: null,
  },
  {
    id: "seed-2",
    position: [38.0357, -78.5034],
    type: "Suspicious Activity",
    location: "Alderman Area",
    severity: 4,
    riskLabel: "security",
    confidence: null,
  },
];

function toCoords(incident: IncidentPayload): [number, number] | null {
  const latitude = typeof incident.latitude === "number" ? incident.latitude : incident.lat;
  const longitude = typeof incident.longitude === "number" ? incident.longitude : incident.lng;
  if (typeof latitude !== "number" || typeof longitude !== "number") return null;
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return null;
  return [latitude, longitude];
}

function toMapReport(payload: unknown): MapReport | null {
  if (!payload || typeof payload !== "object") return null;

  const eventPayload = payload as SocketEventPayload & IncidentPayload;
  const incident =
    eventPayload.incident && typeof eventPayload.incident === "object"
      ? eventPayload.incident
      : (eventPayload as IncidentPayload);

  const coords = toCoords(incident);
  if (!coords) return null;

  const incidentId = incident.id ?? `${incident.title || "incident"}-${incident.created_at || Date.now()}`;
  const severity = typeof incident.severity === "number" ? Math.max(1, Math.min(incident.severity, 5)) : 3;
  const socketScoreConfidence =
    eventPayload.score && typeof eventPayload.score.confidence === "number"
      ? eventPayload.score.confidence
      : null;
  const incidentScoreConfidence =
    typeof incident.score_confidence === "number"
      ? incident.score_confidence
      : null;
  const confidence = socketScoreConfidence ?? incidentScoreConfidence;

  return {
    id: String(incidentId),
    position: coords,
    type: incident.title || "Incident",
    location: incident.location || "Unknown location",
    severity,
    riskLabel: incident.risk_label || "unknown",
    confidence: confidence !== null ? Math.max(0, Math.min(confidence, 1)) : null,
  };
}

export default function HoosAlertPage() {
  const [reports, setReports] = useState<MapReport[]>(initialReports);
  const [socketStatus, setSocketStatus] = useState<"connecting" | "connected" | "disconnected">("connecting");
  const upsertReport = useCallback((report: MapReport) => {
    setReports((prev) => {
      const existingIndex = prev.findIndex((item) => item.id === report.id);
      if (existingIndex >= 0) {
        const next = [...prev];
        next[existingIndex] = report;
        return next;
      }
      return [report, ...prev].slice(0, 200);
    });
  }, []);

  useEffect(() => {
    try {
      const pendingEvent = sessionStorage.getItem(PENDING_EVENT_KEY);
      if (!pendingEvent) return;

      sessionStorage.removeItem(PENDING_EVENT_KEY);
      const parsed = JSON.parse(pendingEvent);
      const report = toMapReport(parsed);
      if (!report) return;

      upsertReport(report);
    } catch {
      // Ignore invalid pending event payloads.
    }
  }, [upsertReport]);

  useEffect(() => {
    setSocketStatus("connecting");
    const socket = new WebSocket(WS_URL);

    socket.onopen = () => setSocketStatus("connected");
    socket.onclose = () => setSocketStatus("disconnected");
    socket.onerror = () => setSocketStatus("disconnected");

    socket.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        const report = toMapReport(parsed);
        if (!report) return;

        upsertReport(report);
      } catch {
        // Ignore malformed websocket payloads.
      }
    };

    return () => {
      socket.close();
    };
  }, [upsertReport]);

  const statusText = useMemo(() => {
    if (socketStatus === "connected") return "Live updates connected";
    if (socketStatus === "connecting") return "Connecting to live updates...";
    return "Live updates disconnected";
  }, [socketStatus]);

  return (
    <div className="h-screen flex flex-col bg-background pt-6">
      <div className="px-5 pb-2 text-sm text-muted-foreground">{statusText}</div>

      <main className="h-[80%] flex gap-5 p-5 pt-0">
        <div className="w-3/4 h-full">
          <div className="h-full w-full">
            <IncidentLiveMap reports={reports} />
          </div>
        </div>

        <div className="w-1/4 h-full">
          <Sidebar />
        </div>
      </main>
    </div>
  );
}
