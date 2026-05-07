interface ActionButtonsProps {
  onRescan: () => void;
  onScanLive: () => void;
  loading: boolean;
}

export function ActionButtons({ onRescan, onScanLive, loading }: ActionButtonsProps) {
  return (
    <div className="mt-4 grid grid-cols-3 gap-3">
      <button
        onClick={onScanLive}
        disabled={loading}
        className="flex items-center justify-center gap-2 rounded-xl border border-ink-700 bg-ink-850 px-4 py-3 text-sm font-medium text-ink-100 transition-all hover:border-ink-600 hover:bg-ink-800 active:scale-[0.98] disabled:opacity-50"
      >
        <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M23 7l-7 5 7 5V7zM14 5H3a2 2 0 00-2 2v10a2 2 0 002 2h11a2 2 0 002-2V7a2 2 0 00-2-2z" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        Scan live
      </button>

      <button
        disabled
        className="flex items-center justify-center gap-2 rounded-xl border border-ink-800 bg-ink-900 px-4 py-3 text-sm font-medium text-ink-400"
      >
        <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10" />
          <polyline points="12 6 12 12 16 14" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        History
      </button>

      <button
        onClick={onRescan}
        disabled={loading}
        className="flex items-center justify-center gap-2 rounded-xl border border-ink-700 bg-ink-850 px-4 py-3 text-sm font-medium text-ink-100 transition-all hover:border-ink-600 hover:bg-ink-800 active:scale-[0.98] disabled:opacity-50"
      >
        <svg viewBox="0 0 24 24" className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} fill="none" stroke="currentColor" strokeWidth="2">
          <polyline points="23 4 23 10 17 10" strokeLinecap="round" strokeLinejoin="round" />
          <polyline points="1 20 1 14 7 14" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        {loading ? "Scanning..." : "Rescan"}
      </button>
    </div>
  );
}
