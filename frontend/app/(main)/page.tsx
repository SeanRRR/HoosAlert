"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import type { MapReport } from "@/components/incident-live-map";
import { Sidebar } from "@/components/sidebar";
import { locationCoords } from "@/lib/location-coords";

type IncidentPayload = {
  id?: string | number;
  _id?: string | number;
  title?: string;
  location?: string;
  location_key?: string;
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
  event_type?: string;
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

const initialReports: MapReport[] = [];

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

  const keyedCoords = incident.location_key ? locationCoords[incident.location_key] : null;
  const coords = keyedCoords ? ([keyedCoords.lat, keyedCoords.lng] as [number, number]) : toCoords(incident);
  if (!coords) return null;

  const incidentId =
    incident.id ??
    incident._id ??
    `${incident.title || "incident"}-${incident.created_at || Date.now()}`;
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
    updatedAt: incident.created_at ?? null,
  };
}

export default function HoosAlertPage() {
  const [reports, setReports] = useState<MapReport[]>(initialReports);
  const [socketStatus, setSocketStatus] = useState<"connecting" | "connected" | "disconnected">("connecting");

  const upsertReports = useCallback((incoming: MapReport[]) => {
    setReports((prev) => {
      let next = [...prev];
      for (const report of incoming) {
        const existingIndex = next.findIndex((item) => item.id === report.id);
        if (existingIndex >= 0) {
          next[existingIndex] = report;
        } else {
          next = [report, ...next];
        }
      }
      return next.slice(0, 200);
    });
  }, []);

  const upsertReport = useCallback((report: MapReport) => {
    upsertReports([report]);
  }, [upsertReports]);

  useEffect(() => {
    let ignore = false;

    async function loadExistingIncidents() {
      try {
        const response = await fetch(`${API_BASE_URL}/api/incidents?limit=200`, {
          cache: "no-store",
        });
        if (!response.ok) return;

        const body: unknown = await response.json();
        if (!body || typeof body !== "object") return;

        const incidents = Array.isArray((body as { incidents?: unknown }).incidents)
          ? ((body as { incidents: unknown[] }).incidents ?? [])
          : [];

        const parsedReports = incidents
          .map((item) => toMapReport(item))
          .filter((item): item is MapReport => item !== null);

        if (ignore || parsedReports.length === 0) return;
        upsertReports(parsedReports);
      } catch {
        // Keep current map state when initial incident load fails.
      }
    }

    loadExistingIncidents();
    return () => {
      ignore = true;
    };
  }, [upsertReports]);

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
        const parsed: unknown = JSON.parse(event.data);
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
          <Sidebar reports={reports} />
        </div>
      </main>
    </div>
  );
}
