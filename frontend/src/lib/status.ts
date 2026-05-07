import type { Biomarkers, BloodPressure } from "../types/api";

export type Status = "normal" | "warning" | "danger";

/**
 * Classify each biomarker against clinically informed thresholds.
 * These are NOT diagnostic — for the demo only, and are documented as
 * such in the project writeup.
 */

export function classifyHeartRate(bpm: number): Status {
  if (bpm < 50 || bpm > 100) return "warning";
  if (bpm < 40 || bpm > 120) return "danger";
  return "normal";
}

export function classifyHRV(sdnnMs: number): Status {
  if (sdnnMs < 20) return "danger";
  if (sdnnMs < 40) return "warning";
  return "normal";
}

export function classifyStress(index: number): Status {
  if (index >= 0.75) return "danger";
  if (index >= 0.5) return "warning";
  return "normal";
}

export function classifyBP(bp: BloodPressure): Status {
  // Loose mapping to AHA categories
  // Stage 2: ≥140 systolic OR ≥90 diastolic
  // Stage 1: 130-139 systolic OR 80-89 diastolic
  // Elevated: 120-129 systolic AND <80 diastolic
  if (bp.systolic >= 140 || bp.diastolic >= 90) return "danger";
  if (bp.systolic >= 130 || bp.diastolic >= 80) return "warning";
  return "normal";
}

export function overallStatus(b: Biomarkers): Status {
  const statuses = [
    classifyHeartRate(b.heart_rate),
    classifyHRV(b.hrv_sdnn),
    classifyStress(b.stress_index),
    classifyBP(b.blood_pressure),
  ];
  if (statuses.includes("danger")) return "danger";
  if (statuses.includes("warning")) return "warning";
  return "normal";
}

export function statusLabel(status: Status): string {
  return { normal: "Normal", warning: "Elevated", danger: "Critical" }[status];
}

export function bpLabel(bp: BloodPressure): string {
  if (bp.systolic >= 140 || bp.diastolic >= 90) return "Stage 1 hypertension";
  if (bp.systolic >= 130 || bp.diastolic >= 80) return "Elevated";
  if (bp.systolic >= 120) return "Mildly elevated";
  return "Normal range";
}

export function statusColor(status: Status) {
  return {
    normal: { fg: "text-status-normal", bg: "bg-status-normal/10", marker: "#34D399" },
    warning: { fg: "text-status-warning", bg: "bg-status-warning/10", marker: "#FBBF24" },
    danger: { fg: "text-status-danger", bg: "bg-status-danger/10", marker: "#F87171" },
  }[status];
}
