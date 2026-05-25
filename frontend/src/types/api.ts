/**
 * Shared API contract types for VitalScan.
 *
 * These types match the JSON schema defined in the project brief and shared
 * across all four groups. Group 1 (rPPG) produces `BiomarkerResponse`.
 * Group 2 (food) produces `FoodResponse`. Groups 3 and 4 consume both.
 *
 * Contract revision (2026-05-25): each biomarker is now a `{value,
 * confidence, unit}` object instead of a flat value, so downstream
 * consumers know how much to trust each measurement.
 *
 * If the contract changes, update this file FIRST — the rest of the app
 * follows from it.
 */

export interface BloodPressureValue {
  systolic: number;
  diastolic: number;
}

/** Numeric biomarker: HR (bpm), HRV (ms), stress (0–1). */
export interface ScalarBiomarker {
  value: number;
  /** 0.0 – 1.0. Higher = the pipeline trusts this measurement more. */
  confidence: number;
  unit: string;
}

/** Blood pressure has a 2-field value; currently a flagged placeholder. */
export interface BloodPressureBiomarker {
  value: BloodPressureValue;
  /** Low (≤0.10) signals "placeholder" — classical rPPG cannot derive BP. */
  confidence: number;
  unit: string;
  /** Optional note from the backend, present when value is a placeholder. */
  note?: string;
}

export interface Biomarkers {
  heart_rate: ScalarBiomarker; // BPM
  hrv_sdnn: ScalarBiomarker; // milliseconds
  stress_index: ScalarBiomarker; // 0.0 – 1.0
  blood_pressure: BloodPressureBiomarker;
}

export interface BiomarkerResponse {
  biomarkers: Biomarkers;
}

/** Group 2 contract — Food Recognition AI output. Included for completeness. */
export interface FoodResponse {
  food: {
    name: string;
    sodium_mg: number;
    sugar_g: number;
    carbs_g: number;
    calories: number;
    fat_g?: number;
  };
}

/** Top-level contract for the integrated app — what Groups 3+4 consume. */
export interface VitalScanContract {
  biomarkers: Biomarkers;
  food?: FoodResponse["food"];
  conditions?: string[]; // e.g. ["diabetes", "hypertension"]
}
