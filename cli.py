#!/usr/bin/env python3
"""
Command-Line Interface for Clinical Quality eCQM / CQL Engine
============================================================
Supports cohort calculation, single-patient evaluation, interactive mode,
gap-in-care analytics, and JSON export for CMS/ONC quality measures.
"""

import sys
import os
import json
import csv
import argparse
from typing import Dict, List, Any

# Ensure project path is accessible
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from ecqm_cql_engine import (
    CQLEquivalentEngine,
    PatientRecord,
    EncounterRecord,
    ConditionRecord,
    ObservationRecord,
    ProcedureRecord,
    MedicationRecord,
    MeasurementPeriod,
    PopulationMeasureScore,
    parse_patient_dict,
)


def get_sample_cohort() -> List[Dict[str, Any]]:
    return [
        {
            "patient_id": "PT-COHORT-01",
            "birth_date": "1965-04-12",
            "gender": "male",
            "encounters": [{"code": "99213", "period_start": "2026-03-15"}],
            "conditions": [{"code": "I10", "onset_date": "2020-01-01", "clinical_status": "active"}],
            "observations": [
                {"code": "8480-6", "value": 128.0, "date": "2026-03-15"},
                {"code": "8462-4", "value": 82.0, "date": "2026-03-15"}
            ],
            "procedures": [{"code": "45378", "performed_date": "2022-05-10"}],  # Colonoscopy 4y ago
            "medications": [{"code": "lisinopril", "authored_date": "2026-03-15"}]
        },
        {
            "patient_id": "PT-COHORT-02",
            "birth_date": "1972-08-25",
            "gender": "female",
            "encounters": [{"code": "99214", "period_start": "2026-02-10"}],
            "conditions": [
                {"code": "E11.9", "onset_date": "2018-09-01", "clinical_status": "active"},
                {"code": "I10", "onset_date": "2019-01-01", "clinical_status": "active"}
            ],
            "observations": [
                {"code": "4548-4", "value": 7.4, "date": "2026-02-10"},  # HbA1c controlled
                {"code": "8480-6", "value": 152.0, "date": "2026-02-10"}, # SBP High
                {"code": "8462-4", "value": 96.0, "date": "2026-02-10"}  # DBP High
            ],
            "procedures": [
                {"code": "77067", "performed_date": "2025-06-10"}  # Mammogram within lookback
            ],
            "medications": [{"code": "metformin", "authored_date": "2026-02-10"}]
        },
        {
            "patient_id": "PT-COHORT-03",
            "birth_date": "1958-11-03",
            "gender": "female",
            "encounters": [{"code": "99203", "period_start": "2026-05-20"}],
            "conditions": [
                {"code": "E11.65", "onset_date": "2015-04-10", "clinical_status": "active"}
            ],
            "observations": [
                {"code": "4548-4", "value": 10.2, "date": "2026-05-20"} # HbA1c Poor Control
            ],
            "procedures": [],
            "medications": []
        },
        {
            "patient_id": "PT-COHORT-04",
            "birth_date": "1995-02-14",
            "gender": "male",
            "encounters": [{"code": "99212", "period_start": "2026-01-10"}],
            "conditions": [],
            "observations": [],
            "procedures": [],
            "medications": []
        }
    ]


def format_measure_report(score: PopulationMeasureScore) -> str:
    lines = []
    lines.append("=" * 78)
    lines.append(f" eCQM QUALITY MEASURE REPORT - {score.measure_id}")
    lines.append(f" Title: {score.measure_title}")
    lines.append(f" Measurement Period: {score.measurement_period.start_date} to {score.measurement_period.end_date}")
    lines.append(f" Improvement Notation: Higher is Better ({score.improvement_notation.value.upper()})")
    lines.append("=" * 78)
    lines.append("POPULATION CRITERIA COUNTS:")
    lines.append(f"  * Initial Population (IPP)  : {score.initial_population_count}")
    lines.append(f"  * Denominator (DENOM)       : {score.denominator_count}")
    lines.append(f"  * Denominator Exclusions    : {score.denominator_exclusion_count}")
    lines.append(f"  * Denominator Exceptions    : {score.denominator_exception_count}")
    lines.append(f"  * Effective Denominator     : {score.effective_denominator_count}")
    lines.append(f"  * Numerator (NUMER)         : {score.numerator_count}")
    lines.append(f"  * Numerator Exclusions      : {score.numerator_exclusion_count}")
    lines.append(f"  * Gaps in Care Identified   : {score.gap_in_care_count}")
    lines.append("-" * 78)
    lines.append(f"PERFORMANCE RATE: {score.performance_rate_pct:.2f}%")
    lines.append("-" * 78)
    lines.append("PATIENT EVALUATION BREAKDOWN:")
    for res in score.patient_results:
        status_str = "NUMERATOR" if res.in_numerator else ("GAP IN CARE" if res.is_gap_in_care else ("EXCLUDED" if res.in_denominator_exclusion else "NOT IN IPP"))
        lines.append(f"  [{res.patient_id}] -> Status: {status_str:<12} | IPP: {res.in_initial_population} | DENOM: {res.in_denominator} | NUM: {res.in_numerator}")
        for r in res.rationale:
            lines.append(f"      - {r}")
    lines.append("=" * 78)
    return "\n".join(lines)


def interactive_mode():
    print("\n--- Interactive eCQM / CQL Patient Evaluator ---")
    pid = input("Enter Patient ID [e.g. PT-TEST-01]: ").strip() or "PT-TEST-01"
    bdate = input("Enter Birth Date (YYYY-MM-DD) [e.g. 1968-05-15]: ").strip() or "1968-05-15"
    gender = input("Enter Gender (male/female) [default female]: ").strip().lower() or "female"

    pt = PatientRecord(
        patient_id=pid,
        birth_date=bdate,
        gender=gender,
        encounters=[EncounterRecord("ambulatory", "99213", "CPT", "2026-04-10")],
    )

    print("\nSelect Conditions (comma-separated numbers):")
    print("  1. Diabetes Mellitus (E11.9)")
    print("  2. Essential Hypertension (I10)")
    print("  3. Colorectal Cancer (C18.9)")
    print("  4. Bilateral Mastectomy (19300)")
    print("  5. None")
    cond_choice = input("Choice [default 5]: ").strip() or "5"
    if "1" in cond_choice:
        pt.conditions.append(ConditionRecord("E11.9", "ICD-10-CM", "2020-01-01"))
    if "2" in cond_choice:
        pt.conditions.append(ConditionRecord("I10", "ICD-10-CM", "2020-01-01"))
    if "3" in cond_choice:
        pt.conditions.append(ConditionRecord("C18.9", "ICD-10-CM", "2022-01-01"))
    if "4" in cond_choice:
        pt.procedures.append(ProcedureRecord("19300", "CPT", "2021-01-01"))

    print("\nSelect Procedures / Screenings (comma-separated):")
    print("  1. Colonoscopy in last 10 years")
    print("  2. Screening Mammogram in last 27 months")
    print("  3. None")
    proc_choice = input("Choice [default 3]: ").strip() or "3"
    if "1" in proc_choice:
        pt.procedures.append(ProcedureRecord("45378", "CPT", "2024-03-15"))
    if "2" in proc_choice:
        pt.procedures.append(ProcedureRecord("77067", "CPT", "2025-05-20"))

    hba1c = input("\nEnter most recent HbA1c (%) if any [e.g. 7.2 or leave blank]: ").strip()
    if hba1c:
        pt.observations.append(ObservationRecord("4548-4", "LOINC", float(hba1c), "2026-04-10"))

    bp = input("Enter Blood Pressure (e.g. 120/80 or leave blank): ").strip()
    if bp and "/" in bp:
        sbp, dbp = bp.split("/")
        pt.observations.append(ObservationRecord("8480-6", "LOINC", float(sbp), "2026-04-10"))
        pt.observations.append(ObservationRecord("8462-4", "LOINC", float(dbp), "2026-04-10"))

    mp = MeasurementPeriod()
    print("\n--- Evaluating Patient Across Standard Measures ---")
    for m_id in ["CMS130v11", "CMS122v11", "CMS125v11", "CMS165v11", "CMS68v12"]:
        score = CQLEquivalentEngine.evaluate_population_cohort(m_id, [pt], mp)
        print(f"\n>> {m_id} ({score.measure_title}):")
        res = score.patient_results[0]
        status = "NUMERATOR MET" if res.in_numerator else ("GAP IN CARE" if res.is_gap_in_care else ("EXCLUDED" if res.in_denominator_exclusion else "NOT IN POPULATION"))
        print(f"   Result: {status}")
        for r in res.rationale:
            print(f"   * {r}")


def load_patients_from_csv(filepath: str) -> List[PatientRecord]:
    """Parse patient records from CSV with eCQM clinical observations."""
    patients_map: Dict[str, PatientRecord] = {}
    with open(filepath, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row.get("patient_id") or row.get("target_identifier") or "PT-UNKNOWN"
            if pid not in patients_map:
                patients_map[pid] = PatientRecord(
                    patient_id=pid,
                    birth_date=row.get("birth_date", "1970-01-01"),
                    gender=row.get("gender", "unknown"),
                )
            pt = patients_map[pid]
            # Encounters
            enc_code = row.get("encounter_code")
            if enc_code:
                pt.encounters.append(EncounterRecord(
                    encounter_type="ambulatory",
                    code=enc_code,
                    code_system="CPT",
                    period_start=row.get("encounter_date", "2026-06-01")
                ))
            # Conditions
            cond_code = row.get("condition_code")
            if cond_code:
                pt.conditions.append(ConditionRecord(
                    code=cond_code,
                    code_system="ICD-10-CM",
                    onset_date=row.get("condition_date", "2020-01-01"),
                    clinical_status=row.get("condition_status", "active")
                ))
            # Observations
            obs_code = row.get("observation_code")
            obs_val = row.get("observation_value")
            if obs_code and obs_val is not None and obs_val != "":
                try:
                    val_float = float(obs_val)
                except ValueError:
                    val_float = 0.0
                pt.observations.append(ObservationRecord(
                    code=obs_code,
                    code_system="LOINC",
                    value=val_float,
                    date=row.get("observation_date", "2026-06-01")
                ))
            # Procedures
            proc_code = row.get("procedure_code")
            if proc_code:
                pt.procedures.append(ProcedureRecord(
                    code=proc_code,
                    code_system="CPT",
                    performed_date=row.get("procedure_date", "2026-06-01")
                ))
            # Medications
            med_code = row.get("medication_code")
            if med_code:
                pt.medications.append(MedicationRecord(
                    code=med_code,
                    code_system="RxNorm",
                    authored_date=row.get("medication_date", "2026-06-01")
                ))
    return list(patients_map.values())


def run_batch_evaluation(input_file: str, output_file: str, measure_id: str = "CMS130v11") -> int:
    """Evaluate batch CSV input and write quality scores & care gaps to output CSV."""
    patients = load_patients_from_csv(input_file)
    mp = MeasurementPeriod()
    score = CQLEquivalentEngine.evaluate_population_cohort(measure_id, patients, mp)

    fieldnames = [
        "patient_id",
        "measure_id",
        "in_initial_population",
        "in_denominator",
        "in_denominator_exclusion",
        "in_denominator_exception",
        "in_numerator",
        "in_numerator_exclusion",
        "is_gap_in_care",
        "rationale",
    ]

    with open(output_file, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for res in score.patient_results:
            writer.writerow({
                "patient_id": res.patient_id,
                "measure_id": res.measure_id,
                "in_initial_population": res.in_initial_population,
                "in_denominator": res.in_denominator,
                "in_denominator_exclusion": res.in_denominator_exclusion,
                "in_denominator_exception": res.in_denominator_exception,
                "in_numerator": res.in_numerator,
                "in_numerator_exclusion": res.in_numerator_exclusion,
                "is_gap_in_care": res.is_gap_in_care,
                "rationale": " | ".join(res.rationale),
            })

    print(f"Batch evaluation completed: {len(score.patient_results)} patients evaluated.")
    print(f"Measure: {score.measure_id} ({score.measure_title}) | Performance Rate: {score.performance_rate_pct:.2f}% | Care Gaps: {score.gap_in_care_count}")
    print(f"Results successfully exported to {output_file}")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Clinical Quality eCQM & CQL Measure Execution Engine"
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # Batch subcommand
    p_batch = subparsers.add_parser("batch", help="Batch evaluate patient records from CSV/JSON")
    p_batch.add_argument("-i", "--input", required=True, help="Path to input CSV or JSON patient data")
    p_batch.add_argument("-o", "--output", default="results.csv", help="Path to output CSV results file")
    p_batch.add_argument("--measure", default="CMS130v11", help="Target eCQM (e.g. CMS130v11, CMS122v11, CMS125v11, CMS165v11, CMS68v12)")

    # Root flags
    parser.add_argument("--demo", action="store_true", help="Run quality measures on a multi-patient sample cohort")
    parser.add_argument("--measure", type=str, default="CMS130v11", help="Target eCQM (CMS130v11, CMS122v11, CMS125v11, CMS165v11, CMS68v12)")
    parser.add_argument("--file", type=str, help="Path to patient/cohort JSON/CSV file to evaluate")
    parser.add_argument("-i", "--input", type=str, help="Alias for --file / input file")
    parser.add_argument("-o", "--output", type=str, help="Output destination file")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--interactive", action="store_true", help="Interactive single-patient evaluation prompt")
    parser.add_argument("--list-measures", action="store_true", help="List supported eCQMs and clinical specifications")

    args = parser.parse_args()

    if args.subcommand == "batch":
        return run_batch_evaluation(args.input, args.output, args.measure)

    if args.list_measures:
        print("\n=== Supported eCQM Measure Specifications ===")
        print("  * CMS130v11: Colorectal Cancer Screening (Age 45-75)")
        print("  * CMS122v11: Diabetes: Hemoglobin A1c Poor Control > 9.0% (Age 18-75, Inverse)")
        print("  * CMS125v11: Breast Cancer Screening (Females Age 52-74)")
        print("  * CMS165v11: Controlling High Blood Pressure (Age 18-85, BP < 140/90)")
        print("  * CMS68v12:  Documentation of Current Medications in the Medical Record")
        return 0

    if args.interactive:
        interactive_mode()
        return 0

    target_file = args.file or args.input
    if target_file and args.output:
        return run_batch_evaluation(target_file, args.output, args.measure)

    mp = MeasurementPeriod()

    if target_file:
        if target_file.endswith(".csv"):
            patients = load_patients_from_csv(target_file)
        else:
            with open(target_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, list):
                patients = [parse_patient_dict(p) for p in raw]
            else:
                patients = [parse_patient_dict(raw)]
    else:
        patients = [parse_patient_dict(p) for p in get_sample_cohort()]

    score = CQLEquivalentEngine.evaluate_population_cohort(args.measure, patients, mp)

    if args.json:
        print(json.dumps(score.to_dict(), indent=2))
    else:
        print(format_measure_report(score))
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
