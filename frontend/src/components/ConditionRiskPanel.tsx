import type { Biomarkers } from "../types/api";
import { classifyBP, classifyHRV, classifyStress } from "../lib/status";

interface ConditionRiskPanelProps {
  biomarkers: Biomarkers | null;
}

/**
 * Condition risk badges. In the integrated app, these scores would come
 * from Group 3's biomarker risk model. For Group 1's standalone demo we
 * derive a simple score from the biomarkers themselves so the dashboard
 * is functional end-to-end.
 *
 * When Group 3's API is live, swap `deriveRisk` for a real fetch call.
 */
function deriveRisk(biomarkers: Biomarkers | null): {
  diabetes: number;
  hypertension: number;
} {
  if (!biomarkers) return { diabetes: 0, hypertension: 0 };

  const bpStatus = classifyBP(biomarkers.blood_pressure);
  const hrvStatus = classifyHRV(biomarkers.hrv_sdnn);
  const stressStatus = classifyStress(biomarkers.stress_index);

  // Hypertension: dominated by BP, modulated by HRV/stress
  const bpScore = bpStatus === "danger" ? 0.8 : bpStatus === "warning" ? 0.5 : 0.15;
  const hrvScore = hrvStatus === "danger" ? 0.2 : hrvStatus === "warning" ? 0.1 : 0;
  const stressScore = stressStatus === "danger" ? 0.1 : stressStatus === "warning" ? 0.05 : 0;
  const hypertension = Math.min(1, bpScore + hrvScore + stressScore);

  // Diabetes: weak rPPG signal, real model would use blood glucose etc.
  const diabetes = Math.min(1, 0.2 + 0.3 * biomarkers.stress_index + (bpStatus !== "normal" ? 0.15 : 0));

  return { diabetes, hypertension };
}

function riskLabel(score: number): { label: string; color: string; bg: string } {
  if (score >= 0.7) return { label: "Elevated risk", color: "text-status-danger", bg: "bg-status-danger/10 border-status-danger/30" };
  if (score >= 0.4) return { label: "Moderate risk", color: "text-status-warning", bg: "bg-status-warning/10 border-status-warning/30" };
  return { label: "Low risk", color: "text-status-normal", bg: "bg-status-normal/10 border-status-normal/30" };
}

export function ConditionRiskPanel({ biomarkers }: ConditionRiskPanelProps) {
  const risks = deriveRisk(biomarkers);

  return (
    <section className="mt-4 rounded-2xl border border-ink-800 bg-ink-900/60 p-5 animate-fade-in">
      <h2 className="text-xs font-medium uppercase tracking-wider text-ink-400">Condition risk</h2>

      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <RiskCard name="Diabetes" score={risks.diabetes} />
        <RiskCard name="Hypertension" score={risks.hypertension} />
      </div>
    </section>
  );
}

function RiskCard({ name, score }: { name: string; score: number }) {
  const { label, color, bg } = riskLabel(score);

  return (
    <div className={`rounded-xl border p-4 ${bg}`}>
      <div className="flex items-center justify-between">
        <div>
          <p className={`text-sm font-medium ${color}`}>{name}</p>
          <p className={`mt-0.5 text-xs ${color} opacity-80 tabular`}>
            {label} · {score.toFixed(2)}
          </p>
        </div>
        <svg viewBox="0 0 24 24" className={`h-5 w-5 ${color}`} fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="9" />
          <line x1="12" y1="8" x2="12" y2="12" strokeLinecap="round" />
          <circle cx="12" cy="16" r="0.5" fill="currentColor" />
        </svg>
      </div>

      {/* Tiny progress bar */}
      <div className="mt-3 h-1 overflow-hidden rounded-full bg-ink-800">
        <div
          className={`h-full transition-all duration-700 ${color.replace("text-", "bg-")}`}
          style={{ width: `${Math.round(score * 100)}%` }}
        />
      </div>
    </div>
  );
}
