import { useEffect, useRef, useState } from "react";

interface WebcamCaptureProps {
  onCapture: (videoBlob: Blob) => void;
  onCancel: () => void;
}

const SCAN_DURATION_SECONDS = 30;

/**
 * Phase 5 — Browser webcam capture for live face scanning.
 *
 * Uses MediaRecorder to capture a 30-second video clip from the user's
 * webcam, then posts it to /scan as a Blob. This is the "live scan"
 * feature the assignment hints at in the deliverables.
 *
 * Note: webcam access requires a secure context (HTTPS or localhost).
 * For homelab Traefik deployment, ensure the cert is valid.
 */
export function WebcamCapture({ onCapture, onCancel }: WebcamCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);

  const [secondsLeft, setSecondsLeft] = useState(SCAN_DURATION_SECONDS);
  const [recording, setRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function setupCamera() {
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
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      } catch (e) {
        setError("Camera access denied. Allow camera permissions and try again.");
        console.error(e);
      }
    }

    setupCamera();
    return () => {
      cancelled = true;
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  const startRecording = () => {
    if (!streamRef.current) return;

    chunksRef.current = [];
    const recorder = new MediaRecorder(streamRef.current, { mimeType: "video/webm" });
    recorderRef.current = recorder;

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };

    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: "video/webm" });
      onCapture(blob);
    };

    recorder.start();
    setRecording(true);
    setSecondsLeft(SCAN_DURATION_SECONDS);

    // Countdown
    const interval = setInterval(() => {
      setSecondsLeft((s) => {
        if (s <= 1) {
          clearInterval(interval);
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

        <div className="mt-4 overflow-hidden rounded-xl bg-black">
          <video
            ref={videoRef}
            autoPlay
            muted
            playsInline
            className="aspect-video w-full object-cover"
          />
        </div>

        {error && (
          <p className="mt-3 rounded-lg bg-status-danger/10 p-3 text-sm text-status-danger">
            {error}
          </p>
        )}

        <div className="mt-4 flex items-center justify-between">
          <p className="text-sm text-ink-400">
            {recording ? `Recording... ${secondsLeft}s` : "Hold still and look at the camera"}
          </p>

          {!recording ? (
            <button
              onClick={startRecording}
              disabled={!!error}
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
