"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import type { MapReport } from "@/components/incident-live-map";
import { Sidebar } from "@/components/sidebar";

type IncidentPayload = {
  id?: string | number;
  _id?: string | number;
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
  event_type?: string;
  incident?: IncidentPayload;
  score?: {
    confidence?: number;
    fallback_used?: boolean;
  };
};

type ConfidenceNotification = {
  id: string;
  message: string;
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

  const coords = toCoords(incident);
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
  const [notifications, setNotifications] = useState<ConfidenceNotification[]>([]);
  const confidenceByIdRef = useRef<Map<string, number | null>>(new Map());

  const notifyConfidenceUpdate = useCallback(
    (report: MapReport, before: number, after: number, fallbackUsed: boolean | null) => {
    const notificationId = `${report.id}-${Date.now()}`;
      const fallbackText =
        fallbackUsed === null ? "fallback=unknown" : `fallback=${fallbackUsed ? "true" : "false"}`;
      const message = `${report.type} at ${report.location}: confidence ${Math.round(
        before * 100,
      )}% -> ${Math.round(after * 100)}% (${fallbackText})`;

      setNotifications((prev) => [...prev.slice(-3), { id: notificationId, message }]);

      window.setTimeout(() => {
        setNotifications((prev) => prev.filter((item) => item.id !== notificationId));
      }, 4500);
    },
    [],
  );

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
    const next = new Map<string, number | null>();
    for (const report of reports) {
      next.set(report.id, report.confidence);
    }
    confidenceByIdRef.current = next;
  }, [reports]);

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

        const payload = parsed as SocketEventPayload;
        const isRescoreEvent = payload.event_type === "incident_rescored";
        const fallbackUsed =
          payload.score && typeof payload.score.fallback_used === "boolean"
            ? payload.score.fallback_used
            : null;
        const previousConfidence = confidenceByIdRef.current.get(report.id);
        const currentConfidence = report.confidence;
        const confidenceChanged =
          typeof previousConfidence === "number" &&
          typeof currentConfidence === "number" &&
          Math.abs(previousConfidence - currentConfidence) > 1e-6;

        if (isRescoreEvent && confidenceChanged) {
          notifyConfidenceUpdate(report, previousConfidence, currentConfidence, fallbackUsed);
        }

        upsertReport(report);
      } catch {
        // Ignore malformed websocket payloads.
      }
    };

    return () => {
      socket.close();
    };
  }, [notifyConfidenceUpdate, upsertReport]);

  const statusText = useMemo(() => {
    if (socketStatus === "connected") return "Live updates connected";
    if (socketStatus === "connecting") return "Connecting to live updates...";
    return "Live updates disconnected";
  }, [socketStatus]);

  return (
    <div className="h-screen flex flex-col bg-background pt-6">
      {notifications.length > 0 && (
        <div className="fixed right-4 top-16 z-[1200] space-y-2">
          {notifications.map((item) => (
            <div
              key={item.id}
              className="max-w-sm rounded-md border border-border bg-background/95 px-3 py-2 text-sm shadow-lg backdrop-blur"
            >
              {item.message}
            </div>
          ))}
        </div>
      )}
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
