import { useEffect, useRef, useState } from "react";
import type { ScanProgress as ScanProgressData } from "../lib/api";

interface ScanProgressProps {
  progress: ScanProgressData;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function ScanProgress({ progress }: ScanProgressProps) {
  // Track elapsed time inside the processing phase so the user can see the
  // scan isn't actually frozen.
  const processingStartedAt = useRef<number | null>(null);
  const [elapsedMs, setElapsedMs] = useState(0);

  useEffect(() => {
    if (progress.phase !== "processing") {
      processingStartedAt.current = null;
      setElapsedMs(0);
      return;
    }
    processingStartedAt.current = Date.now();
    setElapsedMs(0);
    const interval = setInterval(() => {
      if (processingStartedAt.current) {
        setElapsedMs(Date.now() - processingStartedAt.current);
      }
    }, 250);
    return () => clearInterval(interval);
  }, [progress.phase]);

  const isUpload = progress.phase === "upload";
  const elapsedSec = (elapsedMs / 1000).toFixed(elapsedMs < 10_000 ? 1 : 0);

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="w-full max-w-xs">
        <div className="h-2 overflow-hidden rounded-full bg-ink-800">
          {isUpload ? (
            <div
              className="h-full rounded-full bg-status-normal transition-[width] duration-200 ease-out"
              style={{ width: `${progress.percent}%` }}
              role="progressbar"
              aria-valuenow={progress.percent}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`Uploading video — ${progress.percent}%`}
            />
          ) : (
            <div
              className="scan-indeterminate-bar h-full w-1/3 rounded-full bg-status-normal"
              role="progressbar"
              aria-label="Analyzing video"
            />
          )}
        </div>
      </div>

      <div className="text-center text-sm">
        {isUpload ? (
          <>
            <p className="font-medium text-ink-100">Uploading video · {progress.percent}%</p>
            <p className="mt-1 text-xs text-ink-400">
              {formatBytes(progress.uploadedBytes)} / {formatBytes(progress.totalBytes)}
            </p>
          </>
        ) : (
          <>
            <p className="font-medium text-ink-100">Analyzing video…</p>
            <p className="mt-1 text-xs text-ink-400">
              Running rPPG pipeline · {elapsedSec}s elapsed
            </p>
          </>
        )}
      </div>
    </div>
  );
}
