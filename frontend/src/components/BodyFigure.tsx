import type { Biomarkers } from "../types/api";
import {
  classifyBP,
  classifyHRV,
  classifyHeartRate,
  classifyStress,
  statusColor,
} from "../lib/status";

interface BodyFigureProps {
  biomarkers: Biomarkers | null;
}

/**
 * Anatomical front-view silhouette with four biomarker markers placed at
 * physiologically meaningful locations:
 *   - Forehead → stress (where the rPPG signal is also strongest)
 *   - Chest    → heart rate (with subtle pulse animation)
 *   - Heart-adjacent → HRV (heart-derived metric)
 *   - Upper arm → BP (where a cuff would sit)
 */
export function BodyFigure({ biomarkers }: BodyFigureProps) {
  const hrColor = biomarkers
    ? statusColor(classifyHeartRate(biomarkers.heart_rate)).marker
    : "#5A5A63";
  const hrvColor = biomarkers
    ? statusColor(classifyHRV(biomarkers.hrv_sdnn)).marker
    : "#5A5A63";
  const stressColor = biomarkers
    ? statusColor(classifyStress(biomarkers.stress_index)).marker
    : "#5A5A63";
  const bpColor = biomarkers
    ? statusColor(classifyBP(biomarkers.blood_pressure)).marker
    : "#5A5A63";

  return (
    <div className="flex items-center justify-center py-2">
      <svg
        viewBox="0 0 240 400"
        className="h-full max-h-[420px] w-full max-w-[240px]"
        role="img"
        aria-label="Body figure with biomarker indicators"
      >
        <defs>
          <radialGradient id="markerGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="white" stopOpacity="0.4" />
            <stop offset="100%" stopColor="white" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* Body silhouette — slate fill on dark background */}
        <g fill="#1C1C20" stroke="#27272D" strokeWidth="1">
          {/* Head */}
          <ellipse cx="120" cy="48" rx="26" ry="28" />
          {/* Neck */}
          <path d="M 108 74 Q 120 80 132 74 L 132 90 L 108 90 Z" />
          {/* Torso */}
          <path d="M 76 90 Q 120 84 164 90 L 168 215 Q 120 224 72 215 Z" />
          {/* Arms (left + right) */}
          <path d="M 50 96 Q 60 92 72 96 L 76 220 Q 64 226 52 220 Z" />
          <path d="M 168 96 Q 180 92 190 96 L 188 220 Q 176 226 164 220 Z" />
          {/* Hips */}
          <path d="M 72 215 L 168 215 L 165 258 Q 120 268 75 258 Z" />
          {/* Legs */}
          <path d="M 78 258 L 116 258 L 116 388 Q 105 392 82 388 Z" />
          <path d="M 124 258 L 162 258 L 158 388 Q 134 392 124 388 Z" />
        </g>

        {/* Annotation lines from markers to off-figure space */}
        <g stroke="#3A3A42" strokeWidth="0.5" strokeDasharray="3,3" fill="none">
          <line x1="120" y1="42" x2="220" y2="20" />
          <line x1="100" y1="142" x2="220" y2="125" />
          <line x1="135" y1="162" x2="220" y2="200" />
          <line x1="58" y1="142" x2="14" y2="125" />
        </g>

        {/* Stress marker — forehead */}
        <Marker cx={120} cy={42} r={9} color={stressColor} label="ST" />

        {/* Heart rate marker — chest, with pulse animation */}
        <g>
          <circle cx={100} cy={142} r={14} fill={hrColor} fillOpacity="0.15" className="animate-pulse-soft" />
          <Marker cx={100} cy={142} r={11} color={hrColor} label="HR" />
        </g>

        {/* HRV marker — heart-adjacent */}
        <Marker cx={135} cy={162} r={8} color={hrvColor} label="HV" />

        {/* BP marker — upper arm */}
        <Marker cx={58} cy={142} r={9} color={bpColor} label="BP" />
      </svg>
    </div>
  );
}

interface MarkerProps {
  cx: number;
  cy: number;
  r: number;
  color: string;
  label: string;
}

function Marker({ cx, cy, r, color, label }: MarkerProps) {
  return (
    <g>
      <circle cx={cx} cy={cy} r={r} fill={color} stroke="#0A0A0B" strokeWidth="2" />
      <text
        x={cx}
        y={cy + 3}
        textAnchor="middle"
        fontSize={r > 10 ? "10" : "9"}
        fontWeight="600"
        fill="#0A0A0B"
        style={{ fontFamily: "Geist, system-ui, sans-serif" }}
      >
        {label}
      </text>
    </g>
  );
}
