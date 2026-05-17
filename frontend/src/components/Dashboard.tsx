import { useState } from "react";
import { useScan } from "../hooks/useScan";
import { overallStatus } from "../lib/status";
import { ActionButtons } from "./ActionButtons";
import { BodyFigure } from "./BodyFigure";
import { ConditionRiskPanel } from "./ConditionRiskPanel";
import { MetricCard } from "./MetricCard";
import { ScanHeader } from "./ScanHeader";
import { ScanProgress } from "./ScanProgress";
import { WebcamCapture } from "./WebcamCapture";

export function Dashboard() {
  const { data, loading, error, lastScanAt, progress, runMockScan, runVideoScan } = useScan();
  const [showWebcam, setShowWebcam] = useState(false);

  const biomarkers = data?.biomarkers ?? null;
  const status = biomarkers ? overallStatus(biomarkers) : "normal";

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <ScanHeader
        status={status}
        lastScanAt={lastScanAt}
        loading={loading}
        error={error}
      />

      {error && (
        <div className="mt-4 flex items-start gap-3 rounded-xl border border-status-danger/30 bg-status-danger/10 p-4">
          <svg viewBox="0 0 24 24" className="mt-0.5 h-5 w-5 flex-shrink-0 text-status-danger" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" strokeLinecap="round" />
            <line x1="12" y1="16" x2="12.01" y2="16" strokeLinecap="round" />
          </svg>
          <div className="flex-1 text-sm text-status-danger">
            <p className="font-medium">Scan failed</p>
            <p className="mt-1 text-status-danger/80">{error}</p>
          </div>
        </div>
      )}

      {progress && (
        <div className="mt-4 rounded-xl border border-ink-800 bg-ink-900/60 p-4 backdrop-blur-sm">
          <ScanProgress progress={progress} />
        </div>
      )}

      <div className="mt-6 grid gap-4 md:grid-cols-[260px_1fr] rounded-2xl border border-ink-800 bg-ink-900/60 p-6 backdrop-blur-sm">
        <BodyFigure biomarkers={biomarkers} />

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {biomarkers ? (
            <>
              <MetricCard
                label="Heart rate"
                value={biomarkers.heart_rate}
                unit="bpm"
                kind="heart_rate"
              />
              <MetricCard
                label="HRV (SDNN)"
                value={biomarkers.hrv_sdnn}
                unit="ms"
                kind="hrv"
              />
              <MetricCard
                label="Stress index"
                value={biomarkers.stress_index.toFixed(2)}
                unit="/ 1.0"
                kind="stress"
              />
              <MetricCard
                label="Blood pressure"
                value={`${biomarkers.blood_pressure.systolic}/${biomarkers.blood_pressure.diastolic}`}
                unit=""
                kind="bp"
              />
            </>
          ) : (
            <div className="col-span-2 text-center text-ink-400">
              {loading && !progress ? "Scanning..." : "No data"}
            </div>
          )}
        </div>
      </div>

      <ConditionRiskPanel biomarkers={biomarkers} />

      <ActionButtons
        onRescan={runMockScan}
        onScanLive={() => setShowWebcam(true)}
        onUpload={(file) => runVideoScan(file)}
        loading={loading}
      />

      {showWebcam && (
        <WebcamCapture
          onCapture={async (blob) => {
            setShowWebcam(false);
            await runVideoScan(blob);
          }}
          onCancel={() => setShowWebcam(false)}
        />
      )}
    </div>
  );
}
