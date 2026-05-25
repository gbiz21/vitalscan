import type { ReactNode } from "react";
import {
  bpLabel,
  classifyBP,
  classifyHRV,
  classifyHeartRate,
  classifyStress,
  statusColor,
} from "../lib/status";
import type { Biomarkers } from "../types/api";

interface MetricCardProps {
  label: string;
  value: number | string;
  unit: string;
  kind: "heart_rate" | "hrv" | "stress" | "bp";
  /** 0–1 confidence the backend assigned to this biomarker. */
  confidence?: number;
  /** Optional explanation (e.g. for BP, why it's a placeholder). */
  note?: string;
}

/** Map confidence to a 3-tier visual band that pairs with the dashboard palette. */
function confidenceTier(c: number): { label: string; color: string; bg: string } {
  if (c >= 0.75) return { label: "High", color: "text-status-normal", bg: "bg-status-normal/15" };
  if (c >= 0.45) return { label: "Medium", color: "text-status-warning", bg: "bg-status-warning/15" };
  return { label: "Low", color: "text-status-danger", bg: "bg-status-danger/15" };
}

const ICONS: Record<MetricCardProps["kind"], ReactNode> = {
  heart_rate: (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" />
    </svg>
  ),
  hrv: (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="3 12 7 12 10 4 14 20 17 12 21 12" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  stress: (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 2a4 4 0 0 0-4 4v1.2A4 4 0 0 0 4 11v1a4 4 0 0 0 2 3.46V18a3 3 0 0 0 3 3h1v-3M12 2a4 4 0 0 1 4 4v1.2A4 4 0 0 1 20 11v1a4 4 0 0 1-2 3.46V18a3 3 0 0 1-3 3h-1v-3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  bp: (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M7 3v18M17 3v18M7 8l10 0M7 16l10 0" strokeLinecap="round" />
    </svg>
  ),
};

const SUBLABELS: Record<MetricCardProps["kind"], (v: number | string, b?: Biomarkers) => string> = {
  heart_rate: (v) => {
    const bpm = Number(v);
    if (bpm < 50) return "Bradycardia";
    if (bpm > 100) return "Tachycardia";
    return "Normal range";
  },
  hrv: (v) => {
    const ms = Number(v);
    if (ms < 20) return "Very low";
    if (ms < 40) return "Below typical";
    return "Healthy range";
  },
  stress: (v) => {
    const idx = Number(v);
    if (idx >= 0.75) return "Elevated";
    if (idx >= 0.5) return "Moderate";
    return "Low";
  },
  bp: (v) => {
    const [sys, dia] = String(v).split("/").map(Number);
    return bpLabel({ systolic: sys, diastolic: dia });
  },
};

function classifyKind(kind: MetricCardProps["kind"], value: number | string) {
  switch (kind) {
    case "heart_rate":
      return classifyHeartRate(Number(value));
    case "hrv":
      return classifyHRV(Number(value));
    case "stress":
      return classifyStress(Number(value));
    case "bp": {
      const [sys, dia] = String(value).split("/").map(Number);
      return classifyBP({ systolic: sys, diastolic: dia });
    }
  }
}

export function MetricCard({ label, value, unit, kind, confidence, note }: MetricCardProps) {
  const status = classifyKind(kind, value);
  const colors = statusColor(status);
  const conf = confidence !== undefined ? confidenceTier(confidence) : null;
  const confPct = confidence !== undefined ? Math.round(confidence * 100) : null;

  return (
    <div
      className="rounded-xl border border-ink-800 bg-ink-850/50 p-4 transition-colors hover:bg-ink-850 animate-scale-in"
      title={note}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className={colors.fg}>{ICONS[kind]}</span>
          <span className="text-xs font-medium uppercase tracking-wide text-ink-400">{label}</span>
        </div>
        {conf && confPct !== null && (
          <span
            className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${conf.bg} ${conf.color}`}
            title={`Pipeline confidence: ${confPct}%`}
          >
            {conf.label} · {confPct}%
          </span>
        )}
      </div>

      <div className="mt-2 flex items-baseline gap-1.5 tabular">
        <span className="font-mono text-2xl font-medium text-ink-50">{value}</span>
        {unit && <span className="text-xs text-ink-400">{unit}</span>}
      </div>

      <p className={`mt-0.5 text-xs ${colors.fg}`}>{SUBLABELS[kind](value)}</p>
    </div>
  );
}
