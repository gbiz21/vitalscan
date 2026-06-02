/**
 * Course-attribution footer — shown on every page at the bottom of the viewport.
 *
 * Kept intentionally small + muted so it stays out of the dashboard's way but
 * gives the professor / classmates a clear attribution when they open the site.
 */
export function Footer() {
  const members = ["Germaine Beazer", "Jason", "Daray", "Abner"];

  return (
    <footer className="mt-12 border-t border-ink-800/60 bg-ink-950/60 px-6 py-6">
      <div className="mx-auto flex max-w-5xl flex-col items-center gap-1.5 text-center">
        <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-ink-300">
          VitalScan · Group 1 — rPPG Signal Extraction
        </p>
        <p className="text-[11px] text-ink-400">
          AIT 500 · Westcliff University · Master of Science in Artificial Intelligence
        </p>
        <p className="mt-2 text-[11px] text-ink-500">
          {members.map((m, i) => (
            <span key={m}>
              {m}
              {i < members.length - 1 && <span className="mx-2 text-ink-700">·</span>}
            </span>
          ))}
        </p>
      </div>
    </footer>
  );
}
