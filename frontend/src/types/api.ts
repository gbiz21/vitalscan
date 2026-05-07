/**
 * Shared API contract types for VitalScan.
 *
 * These types match the JSON schema defined in the project brief and shared
 * across all four groups. Group 1 (rPPG) produces `BiomarkerResponse`.
 * Group 2 (food) produces `FoodResponse`. Groups 3 and 4 consume both.
 *
 * If the contract changes, update this file FIRST — the rest of the app
 * follows from it.
 */

export interface BloodPressure {
  systolic: number;
  diastolic: number;
}

export interface Biomarkers {
  heart_rate: number; // BPM
  hrv_sdnn: number; // milliseconds
  stress_index: number; // 0.0 - 1.0
  blood_pressure: BloodPressure;
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
