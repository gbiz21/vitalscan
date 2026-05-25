import type { BiomarkerResponse } from "../types/api";

/**
 * In dev, Vite proxies /api -> http://localhost:8000.
 * In Docker, set VITE_API_BASE_URL to the backend service URL at build time.
 */
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";

// Mirror of backend/main.py:MAX_VIDEO_SIZE_MB. Kept in sync manually — the
// backend also enforces it, but checking client-side gives instant feedback
// instead of letting the user wait for a doomed 100+ MB upload.
export const MAX_VIDEO_SIZE_MB = 100;

export type ScanPhase = "upload" | "processing";

export interface ScanProgress {
  phase: ScanPhase;
  uploadedBytes: number;
  totalBytes: number;
  /** 0–100 during upload; 100 throughout processing. */
  percent: number;
}

function parseErrorBody(text: string): string {
  let summary = text.slice(0, 300);
  try {
    const parsed = JSON.parse(text);
    if (parsed.detail) {
      summary = typeof parsed.detail === "string"
        ? parsed.detail
        : JSON.stringify(parsed.detail);
    }
  } catch { /* not JSON, use raw text */ }
  return summary;
}

export function scanVideo(
  videoBlob: Blob,
  onProgress?: (p: ScanProgress) => void,
  person?: string,
): Promise<BiomarkerResponse> {
  if (!videoBlob || videoBlob.size === 0) {
    return Promise.reject(new Error("Video is empty (0 bytes). Recording may have failed."));
  }
  const formData = new FormData();
  // For File objects, preserve the original filename (extension matters for the
  // backend's allowed-extension check). For raw webcam Blobs, fall back to webm.
  const filename = videoBlob instanceof File ? videoBlob.name : "scan.webm";
  formData.append("video", videoBlob, filename);
  // Tag the scan with the user's name so it lands in GET /biometrics?person={name}.
  // Backend treats this as optional — empty value just records an anonymous scan.
  if (person && person.trim()) {
    formData.append("person", person.trim());
  }

  return new Promise<BiomarkerResponse>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/scan`);

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress({
          phase: "upload",
          uploadedBytes: e.loaded,
          totalBytes: e.total,
          percent: Math.min(100, Math.round((e.loaded / e.total) * 100)),
        });
      }
    });

    // Upload bytes are flushed — backend is now running the pipeline.
    xhr.upload.addEventListener("load", () => {
      onProgress?.({
        phase: "processing",
        uploadedBytes: videoBlob.size,
        totalBytes: videoBlob.size,
        percent: 100,
      });
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText) as BiomarkerResponse);
        } catch {
          reject(new Error("Invalid JSON in response"));
        }
      } else {
        reject(new Error(`HTTP ${xhr.status}: ${parseErrorBody(xhr.responseText)}`));
      }
    });

    xhr.addEventListener("error", () => reject(new Error("Network error — could not reach /scan")));
    xhr.addEventListener("abort", () => reject(new Error("Upload aborted")));
    xhr.addEventListener("timeout", () => reject(new Error("Upload timed out")));

    xhr.send(formData);
  });
}

export async function fetchMockScan(): Promise<BiomarkerResponse> {
  const response = await fetch(`${API_BASE}/scan/mock`, { method: "POST" });

  if (!response.ok) {
    throw new Error(`Mock scan failed: ${response.status}`);
  }

  return response.json();
}
