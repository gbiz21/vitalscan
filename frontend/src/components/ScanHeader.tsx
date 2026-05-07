import type { Status } from "../lib/status";
import { statusColor, statusLabel } from "../lib/status";

interface ScanHeaderProps {
  status: Status;
  lastScanAt: Date | null;
  loading: boolean;
  error: string | null;
}

function timeSince(date: Date): string {
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  return `${Math.floor(minutes / 60)}h ago`;
}

export function ScanHeader({ status, lastScanAt, loading, error }: ScanHeaderProps) {
  const colors = statusColor(status);

  let subtitle: string;
  if (loading) subtitle = "Scanning...";
  else if (error) subtitle = "Scan error";
  else if (lastScanAt) subtitle = `Scan complete · ${timeSince(lastScanAt)}`;
  else subtitle = "Ready to scan";

  return (
    <header className="flex items-center justify-between animate-fade-in">
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-ink-800 ring-1 ring-ink-700">
          <svg viewBox="0 0 24 24" className="h-5 w-5 text-status-normal" fill="currentColor">
            <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" />
          </svg>
        </div>
        <div>
          <h1 className="text-lg font-medium tracking-tight">VitalScan</h1>
          <p className="text-xs text-ink-400">{subtitle}</p>
        </div>
      </div>

      <div className={`flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium ${colors.bg} ${colors.fg} ring-1 ring-inset ring-current/20`}>
        <span className={`h-1.5 w-1.5 rounded-full ${status !== "normal" ? "animate-pulse-soft" : ""}`} style={{ backgroundColor: colors.marker }} />
        {statusLabel(status)}
      </div>
    </header>
  );
}
