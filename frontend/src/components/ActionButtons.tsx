import { useRef } from "react";

interface ActionButtonsProps {
  onRescan: () => void;
  onScanLive: () => void;
  onUpload: (file: File) => void;
  loading: boolean;
}

const ACCEPTED_VIDEO_TYPES = "video/mp4,video/webm,video/quicktime,video/x-matroska,.mp4,.webm,.mov,.avi,.mkv";

export function ActionButtons({ onRescan, onScanLive, onUpload, loading }: ActionButtonsProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) onUpload(file);
    // Reset so picking the same file twice still triggers onChange
    e.target.value = "";
  };

  return (
    <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
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
        onClick={() => fileInputRef.current?.click()}
        disabled={loading}
        className="flex items-center justify-center gap-2 rounded-xl border border-ink-700 bg-ink-850 px-4 py-3 text-sm font-medium text-ink-100 transition-all hover:border-ink-600 hover:bg-ink-800 active:scale-[0.98] disabled:opacity-50"
      >
        <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        Upload video
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

      <input
        ref={fileInputRef}
        type="file"
        accept={ACCEPTED_VIDEO_TYPES}
        className="hidden"
        onChange={handleFileChange}
      />
    </div>
  );
}
