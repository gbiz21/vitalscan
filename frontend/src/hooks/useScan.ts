import { useCallback, useEffect, useState } from "react";
import { fetchMockScan, scanVideo } from "../lib/api";
import type { BiomarkerResponse } from "../types/api";

export interface ScanState {
  data: BiomarkerResponse | null;
  loading: boolean;
  error: string | null;
  lastScanAt: Date | null;
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
};

export function useScan() {
  const [state, setState] = useState<ScanState>(initialState);

  const runMockScan = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const data = await fetchMockScan();
      const lastScanAt = new Date();
      persist(data, lastScanAt);
      setState({ data, loading: false, error: null, lastScanAt });
    } catch (e) {
      const error = e instanceof Error ? e.message : "Scan failed";
      setState((s) => ({ ...s, loading: false, error }));
    }
  }, []);

  const runVideoScan = useCallback(async (videoBlob: Blob) => {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const data = await scanVideo(videoBlob);
      const lastScanAt = new Date();
      persist(data, lastScanAt);
      setState({ data, loading: false, error: null, lastScanAt });
    } catch (e) {
      const error = e instanceof Error ? e.message : "Scan failed";
      setState((s) => ({ ...s, loading: false, error }));
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
