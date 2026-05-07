import type { BiomarkerResponse } from "../types/api";

/**
 * In dev, Vite proxies /api -> http://localhost:8000.
 * In Docker, set VITE_API_BASE_URL to the backend service URL at build time.
 */
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";

export async function scanVideo(videoBlob: Blob): Promise<BiomarkerResponse> {
  if (!videoBlob || videoBlob.size === 0) {
    throw new Error("Video is empty (0 bytes). Recording may have failed.");
  }
  const formData = new FormData();
  // For File objects, preserve the original filename (extension matters for the
  // backend's allowed-extension check). For raw webcam Blobs, fall back to webm.
  const filename = videoBlob instanceof File ? videoBlob.name : "scan.webm";
  formData.append("video", videoBlob, filename);

  const response = await fetch(`${API_BASE}/scan`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    // FastAPI 422 returns a JSON detail array; surface a readable summary.
    let summary = text.slice(0, 300);
    try {
      const parsed = JSON.parse(text);
      if (parsed.detail) {
        summary = typeof parsed.detail === "string"
          ? parsed.detail
          : JSON.stringify(parsed.detail);
      }
    } catch { /* not JSON, use raw text */ }
    throw new Error(`HTTP ${response.status}: ${summary}`);
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
