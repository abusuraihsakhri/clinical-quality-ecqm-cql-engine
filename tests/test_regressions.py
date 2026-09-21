"""Regression tests for correctness issues found during repository audit."""

import csv

import pytest

from ecqm_cql_engine import (
    CQLExpressionEvaluator,
    CQLEquivalentEngine,
    ConditionRecord,
    EncounterRecord,
    MeasurementPeriod,
    ObservationRecord,
    PatientRecord,
    ProcedureRecord,
)
from ecqm_cql_engine.cli import format_measure_report, load_patients_from_csv


def test_calendar_month_lookback_uses_calendar_boundary():
    assert CQLExpressionEvaluator.is_date_within_lookback_months(
        "2026-02-28", "2026-03-31", 1
    )
    assert not CQLExpressionEvaluator.is_date_within_lookback_months(
        "2026-02-27", "2026-03-31", 1
    )


def test_calendar_year_lookback_uses_anniversary_boundary():
    assert CQLExpressionEvaluator.is_date_within_lookback_years(
        "2016-12-31", "2026-12-31", 10
    )
    assert not CQLExpressionEvaluator.is_date_within_lookback_years(
        "2016-12-30", "2026-12-31", 10
    )


def test_cms130_requires_qualifying_encounter_in_measurement_period():
    patient = PatientRecord(
        patient_id="PT-BAD-ENCOUNTER",
        birth_date="1960-01-01",
        gender="male",
        encounters=[EncounterRecord("other", "99999", "CPT", "2026-06-01")],
    )
    result = CQLEquivalentEngine.evaluate_cms130v11(patient, MeasurementPeriod())
    assert not result.in_initial_population
    assert not result.in_denominator


def test_cms130_rejects_qualifying_code_outside_measurement_period():
    patient = PatientRecord(
        patient_id="PT-OLD-ENCOUNTER",
        birth_date="1960-01-01",
        gender="male",
        encounters=[EncounterRecord("ambulatory", "99213", "CPT", "2025-12-31")],
    )
    result = CQLEquivalentEngine.evaluate_cms130v11(patient, MeasurementPeriod())
    assert not result.in_initial_population


def test_cms130_accepts_procedure_only_fit_dna():
    patient = PatientRecord(
        patient_id="PT-FIT-DNA",
        birth_date="1960-01-01",
        gender="female",
        encounters=[EncounterRecord("ambulatory", "99213", "CPT", "2026-03-01")],
        procedures=[ProcedureRecord("81528", "CPT", "2025-05-01")],
    )
    result = CQLEquivalentEngine.evaluate_cms130v11(patient, MeasurementPeriod())
    assert result.in_numerator
    assert not result.is_gap_in_care


def test_cms165_does_not_treat_diastolic_as_systolic():
    patient = PatientRecord(
        patient_id="PT-DBP-ONLY",
        birth_date="1960-01-01",
        gender="male",
        conditions=[ConditionRecord("I10", "ICD-10-CM", "2020-01-01")],
        observations=[ObservationRecord("8462-4", "LOINC", 78.0, "2026-05-10")],
    )
    result = CQLEquivalentEngine.evaluate_cms165v11(patient, MeasurementPeriod())
    assert not result.in_numerator
    assert result.is_gap_in_care


def test_cms165_requires_systolic_and_diastolic_on_same_date():
    patient = PatientRecord(
        patient_id="PT-SPLIT-BP",
        birth_date="1960-01-01",
        gender="male",
        conditions=[ConditionRecord("I10", "ICD-10-CM", "2020-01-01")],
        observations=[
            ObservationRecord("8480-6", "LOINC", 124.0, "2026-05-10"),
            ObservationRecord("8462-4", "LOINC", 78.0, "2026-05-09"),
        ],
    )
    result = CQLEquivalentEngine.evaluate_cms165v11(patient, MeasurementPeriod())
    assert not result.in_numerator
    assert result.is_gap_in_care


def test_cms68_requires_supported_qualifying_encounter():
    patient = PatientRecord(
        patient_id="PT-MEDS-NONQUAL",
        birth_date="1980-01-01",
        gender="female",
        encounters=[EncounterRecord("other", "99999", "CPT", "2026-03-01")],
    )
    result = CQLEquivalentEngine.evaluate_cms68v12(patient, MeasurementPeriod())
    assert not result.in_initial_population


def test_unsupported_measure_raises_instead_of_silent_fallback():
    with pytest.raises(ValueError, match="Unsupported measure_id"):
        CQLEquivalentEngine.evaluate_population_cohort("CMS999v1", [])


def test_csv_loader_preserves_text_observation_values(tmp_path):
    path = tmp_path / "patients.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "patient_id",
                "birth_date",
                "gender",
                "observation_code",
                "observation_value",
                "observation_date",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "patient_id": "PT-TEXT",
                "birth_date": "1960-01-01",
                "gender": "female",
                "observation_code": "14563-1",
                "observation_value": "Negative",
                "observation_date": "2026-06-01",
            }
        )

    patient = load_patients_from_csv(str(path))[0]
    assert patient.observations[0].value == "Negative"


def test_inverse_measure_report_uses_lower_is_better():
    patient = PatientRecord(
        patient_id="PT-DM",
        birth_date="1970-01-01",
        gender="male",
        conditions=[ConditionRecord("E11.9", "ICD-10-CM", "2019-01-01")],
        observations=[ObservationRecord("4548-4", "LOINC", 7.0, "2026-06-01")],
    )
    score = CQLEquivalentEngine.evaluate_population_cohort(
        "CMS122v11", [patient], MeasurementPeriod()
    )
    report = format_measure_report(score)
    assert "Improvement Notation: Lower is better (DECREASED)" in report

def test_hba1c_nonnumeric_value_becomes_gap_not_exception():
    patient = PatientRecord(
        patient_id="PT-DM-TEXT",
        birth_date="1970-01-01",
        gender="male",
        conditions=[ConditionRecord("E11.9", "ICD-10-CM", "2019-01-01")],
        observations=[ObservationRecord("4548-4", "LOINC", "not available", "2026-06-01")],
    )
    result = CQLEquivalentEngine.evaluate_cms122v11(patient, MeasurementPeriod())
    assert result.in_numerator
    assert result.is_gap_in_care
    assert "non-numeric" in result.rationale[-1]


def test_bp_nonnumeric_value_becomes_gap_not_exception():
    patient = PatientRecord(
        patient_id="PT-BP-TEXT",
        birth_date="1960-01-01",
        gender="male",
        conditions=[ConditionRecord("I10", "ICD-10-CM", "2020-01-01")],
        observations=[
            ObservationRecord("8480-6", "LOINC", "not available", "2026-05-10"),
            ObservationRecord("8462-4", "LOINC", 78.0, "2026-05-10"),
        ],
    )
    result = CQLEquivalentEngine.evaluate_cms165v11(patient, MeasurementPeriod())
    assert not result.in_numerator
    assert result.is_gap_in_care
    assert "non-numeric" in result.rationale[-1]


def test_measurement_period_rejects_reverse_dates():
    with pytest.raises(ValueError, match="start_date"):
        MeasurementPeriod("2026-12-31", "2026-01-01")

