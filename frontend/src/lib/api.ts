import type { BiomarkerResponse } from "../types/api";

/**
 * In dev, Vite proxies /api -> http://localhost:8000.
 * In Docker, set VITE_API_BASE_URL to the backend service URL at build time.
 */
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";

export async function scanVideo(videoBlob: Blob): Promise<BiomarkerResponse> {
  const formData = new FormData();
  formData.append("video", videoBlob, "scan.webm");

  const response = await fetch(`${API_BASE}/scan`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Scan failed (${response.status}): ${detail}`);
  }

  return response.json();
}

export async function fetchMockScan(): Promise<BiomarkerResponse> {
  const response = await fetch(`${API_BASE}/scan/mock`, { method: "POST" });

  if (!response.ok) {
    throw new Error(`Mock scan failed: ${response.status}`);
  }

  return response.json();
}
