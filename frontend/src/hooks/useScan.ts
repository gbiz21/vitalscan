import { useCallback, useEffect, useState } from "react";
import { fetchMockScan, scanVideo } from "../lib/api";
import type { BiomarkerResponse } from "../types/api";

export interface ScanState {
  data: BiomarkerResponse | null;
  loading: boolean;
  error: string | null;
  lastScanAt: Date | null;
}

const initialState: ScanState = {
  data: null,
  loading: false,
  error: null,
  lastScanAt: null,
};

export function useScan() {
  const [state, setState] = useState<ScanState>(initialState);

  const runMockScan = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const data = await fetchMockScan();
      setState({ data, loading: false, error: null, lastScanAt: new Date() });
    } catch (e) {
      const error = e instanceof Error ? e.message : "Scan failed";
      setState((s) => ({ ...s, loading: false, error }));
    }
  }, []);

  const runVideoScan = useCallback(async (videoBlob: Blob) => {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const data = await scanVideo(videoBlob);
      setState({ data, loading: false, error: null, lastScanAt: new Date() });
    } catch (e) {
      const error = e instanceof Error ? e.message : "Scan failed";
      setState((s) => ({ ...s, loading: false, error }));
    }
  }, []);

  // Run an initial mock scan on mount so the dashboard never starts empty
  useEffect(() => {
    runMockScan();
  }, [runMockScan]);

  return { ...state, runMockScan, runVideoScan };
}
