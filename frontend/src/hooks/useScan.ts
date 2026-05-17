import { useCallback, useEffect, useState } from "react";
import { fetchMockScan, MAX_VIDEO_SIZE_MB, scanVideo, type ScanProgress } from "../lib/api";
import type { BiomarkerResponse } from "../types/api";

export interface ScanState {
  data: BiomarkerResponse | null;
  loading: boolean;
  error: string | null;
  lastScanAt: Date | null;
  progress: ScanProgress | null;
}

const STORAGE_KEY = "vitalscan:lastScan";

interface PersistedScan {
  data: BiomarkerResponse;
  lastScanAt: string;
}

function loadPersisted(): { data: BiomarkerResponse; lastScanAt: Date } | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as PersistedScan;
    return { data: parsed.data, lastScanAt: new Date(parsed.lastScanAt) };
  } catch {
    return null;
  }
}

function persist(data: BiomarkerResponse, lastScanAt: Date) {
  try {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ data, lastScanAt: lastScanAt.toISOString() } satisfies PersistedScan),
    );
  } catch {
    // localStorage unavailable (private mode, quota) — degrade silently
  }
}

const persisted = loadPersisted();
const initialState: ScanState = {
  data: persisted?.data ?? null,
  loading: false,
  error: null,
  lastScanAt: persisted?.lastScanAt ?? null,
  progress: null,
};

export function useScan() {
  const [state, setState] = useState<ScanState>(initialState);

  const runMockScan = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: null, progress: null }));
    try {
      const data = await fetchMockScan();
      const lastScanAt = new Date();
      persist(data, lastScanAt);
      setState({ data, loading: false, error: null, lastScanAt, progress: null });
    } catch (e) {
      const error = e instanceof Error ? e.message : "Scan failed";
      setState((s) => ({ ...s, loading: false, error, progress: null }));
    }
  }, []);

  const runVideoScan = useCallback(async (videoBlob: Blob) => {
    // Reject oversized files before we waste bandwidth — the backend caps at
    // MAX_VIDEO_SIZE_MB, and Cloudflare's tunnel adds its own ~100 MB body cap.
    const sizeMB = videoBlob.size / (1024 * 1024);
    if (sizeMB > MAX_VIDEO_SIZE_MB) {
      setState((s) => ({
        ...s,
        loading: false,
        progress: null,
        error: `Video is ${sizeMB.toFixed(1)} MB · max ${MAX_VIDEO_SIZE_MB} MB. ` +
               `Trim the clip to ~30 seconds or use the live webcam capture.`,
      }));
      return;
    }
    // Seed progress at 0% upload so the bar appears immediately, even before
    // the first XHR progress event fires.
    setState((s) => ({
      ...s,
      loading: true,
      error: null,
      progress: {
        phase: "upload",
        uploadedBytes: 0,
        totalBytes: videoBlob.size,
        percent: 0,
      },
    }));
    try {
      const data = await scanVideo(videoBlob, (progress) => {
        setState((s) => ({ ...s, progress }));
      });
      const lastScanAt = new Date();
      persist(data, lastScanAt);
      setState({ data, loading: false, error: null, lastScanAt, progress: null });
    } catch (e) {
      const error = e instanceof Error ? e.message : "Scan failed";
      setState((s) => ({ ...s, loading: false, error, progress: null }));
    }
  }, []);

  // Seed a mock scan only on first-ever load so the dashboard isn't empty.
  // Persisted scans hydrate from localStorage and must not be overwritten on refresh.
  useEffect(() => {
    if (initialState.data === null) {
      runMockScan();
    }
  }, [runMockScan]);

  return { ...state, runMockScan, runVideoScan };
}
