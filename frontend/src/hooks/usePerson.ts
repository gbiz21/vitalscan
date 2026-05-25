import { useCallback, useEffect, useState } from "react";

/**
 * Persist the current user's display name in localStorage.
 *
 * Used to tag every scan with a `person` field so Groups 3+4 can query
 * GET /biometrics?person={name} to retrieve a specific user's scans.
 *
 * Not authentication — just a label. Empty string means anonymous.
 */
const STORAGE_KEY = "vitalscan:person";
const MAX_LEN = 48;

function load(): string {
  try {
    return (localStorage.getItem(STORAGE_KEY) ?? "").slice(0, MAX_LEN);
  } catch {
    return "";
  }
}

function save(value: string) {
  try {
    if (value) localStorage.setItem(STORAGE_KEY, value);
    else localStorage.removeItem(STORAGE_KEY);
  } catch {
    // localStorage unavailable (private mode, quota) — degrade silently
  }
}

export function usePerson() {
  const [person, setPersonState] = useState<string>(load);

  const setPerson = useCallback((next: string) => {
    const trimmed = next.trim().slice(0, MAX_LEN);
    setPersonState(trimmed);
    save(trimmed);
  }, []);

  // Sync across tabs so editing in one window updates the other.
  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY) setPersonState((e.newValue ?? "").slice(0, MAX_LEN));
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  return { person, setPerson };
}
