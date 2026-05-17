import { useEffect, useRef, useState } from "react";

interface WebcamCaptureProps {
  onCapture: (videoBlob: Blob) => void;
  onCancel: () => void;
}

const SCAN_DURATION_SECONDS = 30;

// Probe MIME types in order of preference. Chrome/Edge support video/webm;
// Safari only supports video/mp4 (with the .mp4 extension).
const PREFERRED_MIME_TYPES = [
  "video/webm;codecs=vp9",
  "video/webm;codecs=vp8",
  "video/webm",
  "video/mp4;codecs=h264",
  "video/mp4",
];

function pickSupportedMimeType(): { mimeType: string; ext: string } | null {
  for (const mt of PREFERRED_MIME_TYPES) {
    if (MediaRecorder.isTypeSupported(mt)) {
      return { mimeType: mt, ext: mt.startsWith("video/mp4") ? ".mp4" : ".webm" };
    }
  }
  return null;
}

export function WebcamCapture({ onCapture, onCancel }: WebcamCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const [secondsLeft, setSecondsLeft] = useState(SCAN_DURATION_SECONDS);
  const [recording, setRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cameraReady, setCameraReady] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function setupCamera() {
      // Webcam needs HTTPS or localhost; bail early with a clear message.
      if (!navigator.mediaDevices?.getUserMedia) {
        setError("Webcam requires HTTPS. Open this page over HTTPS or localhost.");
        return;
      }
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "user", width: 640, height: 480 },
          audio: false,
        });
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) videoRef.current.srcObject = stream;
        setCameraReady(true);
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : String(e);
        setError(`Camera access failed: ${msg}`);
        console.error(e);
      }
    }

    setupCamera();
    return () => {
      cancelled = true;
      if (intervalRef.current) clearInterval(intervalRef.current);
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  const startRecording = () => {
    if (!streamRef.current) {
      setError("Camera not ready yet. Wait a moment and try again.");
      return;
    }

    const supported = pickSupportedMimeType();
    if (!supported) {
      setError(
        "Your browser cannot record video (no MediaRecorder mime type supported). " +
          "Use Chrome, Edge, or Firefox — or use Upload video instead.",
      );
      return;
    }

    chunksRef.current = [];
    let recorder: MediaRecorder;
    try {
      recorder = new MediaRecorder(streamRef.current, { mimeType: supported.mimeType });
    } catch (e) {
      setError(`MediaRecorder failed to start: ${e instanceof Error ? e.message : e}`);
      return;
    }
    recorderRef.current = recorder;

    recorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) chunksRef.current.push(e.data);
    };

    recorder.onerror = (e) => {
      setError(`Recording error: ${(e as ErrorEvent).message ?? "unknown"}`);
      setRecording(false);
    };

    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: supported.mimeType });
      // Guard against the 422-empty-upload bug — if no chunks, surface the
      // problem instead of POSTing a 0-byte field that the API rejects.
      if (blob.size < 1024) {
        setError(
          `Recording produced only ${blob.size} bytes. Try Chrome/Firefox, or use Upload video instead.`,
        );
        return;
      }
      // Wrap in a File so the upload preserves the right extension
      // (api.ts uses File.name to set the filename for the multipart field).
      const file = new File([blob], `scan${supported.ext}`, { type: supported.mimeType });
      onCapture(file);
    };

    // Pass timeslice so dataavailable fires every second — we still get a
    // usable blob even if the user cancels mid-recording.
    recorder.start(1000);
    setRecording(true);
    setSecondsLeft(SCAN_DURATION_SECONDS);

    intervalRef.current = setInterval(() => {
      setSecondsLeft((s) => {
        if (s <= 1) {
          if (intervalRef.current) clearInterval(intervalRef.current);
          recorder.stop();
          setRecording(false);
          return 0;
        }
        return s - 1;
      });
    }, 1000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink-950/80 backdrop-blur-md">
      <div className="w-full max-w-lg rounded-2xl border border-ink-800 bg-ink-900 p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-medium">Live face scan</h2>
          <button
            onClick={onCancel}
            className="text-ink-400 hover:text-ink-100"
            aria-label="Close"
          >
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" strokeLinecap="round" />
              <line x1="6" y1="6" x2="18" y2="18" strokeLinecap="round" />
            </svg>
          </button>
        </div>

        <div
          className={`relative mt-4 overflow-hidden rounded-xl bg-black transition-shadow duration-300 ${
            recording ? "shadow-[0_0_24px_2px_rgba(29,158,117,0.45)] ring-1 ring-status-normal/60" : ""
          }`}
        >
          <video
            ref={videoRef}
            autoPlay
            muted
            playsInline
            className="aspect-video w-full object-cover"
          />

          {/* Corner viewfinder brackets — dim when idle, brighten when recording */}
          {cameraReady && !error && (
            <div
              aria-hidden
              className={`pointer-events-none absolute inset-0 transition-opacity duration-300 ${
                recording ? "opacity-100" : "opacity-50"
              }`}
            >
              <span className="absolute left-3 top-3 h-6 w-6 rounded-tl-sm border-l-2 border-t-2 border-status-normal" />
              <span className="absolute right-3 top-3 h-6 w-6 rounded-tr-sm border-r-2 border-t-2 border-status-normal" />
              <span className="absolute bottom-3 left-3 h-6 w-6 rounded-bl-sm border-b-2 border-l-2 border-status-normal" />
              <span className="absolute bottom-3 right-3 h-6 w-6 rounded-br-sm border-b-2 border-r-2 border-status-normal" />
            </div>
          )}

          {/* Sweeping scan line — only during active recording */}
          {recording && (
            <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
              <div
                className="scan-sweep-line h-[2px] w-full bg-gradient-to-r from-transparent via-status-normal to-transparent"
                style={{ boxShadow: "0 0 8px rgba(29, 158, 117, 0.8)" }}
              />
            </div>
          )}

          {/* REC indicator — top-right, mimics camera UIs */}
          {recording && (
            <div
              aria-label="Recording"
              className="pointer-events-none absolute right-3 top-3 flex items-center gap-1.5 rounded-full bg-black/60 px-2 py-1 text-[10px] font-semibold tracking-wider text-ink-100 backdrop-blur-sm"
            >
              <span className="rec-dot h-1.5 w-1.5 rounded-full bg-status-danger" />
              REC
            </div>
          )}
        </div>

        {error && (
          <p className="mt-3 rounded-lg bg-status-danger/10 p-3 text-sm text-status-danger">
            {error}
          </p>
        )}

        <div className="mt-4 flex items-center justify-between">
          <p className="text-sm text-ink-400">
            {recording
              ? `Recording... ${secondsLeft}s`
              : cameraReady
                ? "Hold still and look at the camera"
                : "Starting camera..."}
          </p>

          {!recording ? (
            <button
              onClick={startRecording}
              disabled={!!error || !cameraReady}
              className="rounded-lg bg-status-normal px-4 py-2 text-sm font-medium text-ink-950 hover:bg-status-normal/90 disabled:opacity-50"
            >
              Start 30s scan
            </button>
          ) : (
            <div className="font-mono text-sm text-status-normal tabular">
              {secondsLeft}s
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
