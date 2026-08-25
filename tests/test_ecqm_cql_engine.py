"""
Unit and Integration Test Suite for eCQM & CQL Measure Execution Engine
======================================================================
Tests clinical quality measures (CMS130, CMS122, CMS125, CMS165, CMS68),
temporal logic, population criteria, gap-in-care analytics, and edge cases.
"""

import unittest
import json
import os
import sys

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ecqm_cql_engine import (
    CQLExpressionEvaluator,
    CQLEquivalentEngine,
    PatientRecord,
    EncounterRecord,
    ConditionRecord,
    ObservationRecord,
    ProcedureRecord,
    MedicationRecord,
    MeasurementPeriod,
    PopulationMeasureScore,
    QualityMeasureImprovement,
    parse_patient_dict,
)


class TestCQLTemporalPredicates(unittest.TestCase):
    """Test CQL date comparison and lookback interval evaluators."""

    def test_date_in_interval_true(self):
        self.assertTrue(CQLExpressionEvaluator.is_date_in_interval("2026-06-15", "2026-01-01", "2026-12-31"))

    def test_date_in_interval_boundary(self):
        self.assertTrue(CQLExpressionEvaluator.is_date_in_interval("2026-01-01", "2026-01-01", "2026-12-31"))
        self.assertTrue(CQLExpressionEvaluator.is_date_in_interval("2026-12-31", "2026-01-01", "2026-12-31"))

    def test_date_in_interval_false(self):
        self.assertFalse(CQLExpressionEvaluator.is_date_in_interval("2025-12-31", "2026-01-01", "2026-12-31"))
        self.assertFalse(CQLExpressionEvaluator.is_date_in_interval("2027-01-01", "2026-01-01", "2026-12-31"))

    def test_lookback_months(self):
        # 12 months lookback from 2026-12-31
        self.assertTrue(CQLExpressionEvaluator.is_date_within_lookback_months("2026-02-01", "2026-12-31", 12))
        self.assertTrue(CQLExpressionEvaluator.is_date_within_lookback_months("2025-01-01", "2026-12-31", 27))
        self.assertFalse(CQLExpressionEvaluator.is_date_within_lookback_months("2023-01-01", "2026-12-31", 27))

    def test_lookback_years(self):
        self.assertTrue(CQLExpressionEvaluator.is_date_within_lookback_years("2020-05-10", "2026-12-31", 10))
        self.assertTrue(CQLExpressionEvaluator.is_date_within_lookback_years("2023-01-15", "2026-12-31", 5))
        self.assertFalse(CQLExpressionEvaluator.is_date_within_lookback_years("2015-01-01", "2026-12-31", 10))


class TestCMS130ColorectalScreening(unittest.TestCase):
    """Test CMS130v11 Colorectal Cancer Screening measure."""

    def setUp(self):
        self.mp = MeasurementPeriod("2026-01-01", "2026-12-31")

    def test_age_exclusion(self):
        # Age 40 (under 45)
        pt_young = PatientRecord(
            patient_id="PT-YOUNG",
            birth_date="1986-01-01",
            gender="male",
            encounters=[EncounterRecord("ambulatory", "99213", "CPT", "2026-04-01")],
        )
        res = CQLEquivalentEngine.evaluate_cms130v11(pt_young, self.mp)
        self.assertFalse(res.in_initial_population)
        self.assertFalse(res.in_denominator)

    def test_colonoscopy_numerator(self):
        pt = PatientRecord(
            patient_id="PT-COLO",
            birth_date="1960-05-10",  # Age 65
            gender="male",
            encounters=[EncounterRecord("ambulatory", "99213", "CPT", "2026-03-01")],
            procedures=[ProcedureRecord("45378", "CPT", "2021-04-15")],  # Colonoscopy 5y ago
        )
        res = CQLEquivalentEngine.evaluate_cms130v11(pt, self.mp)
        self.assertTrue(res.in_initial_population)
        self.assertTrue(res.in_denominator)
        self.assertTrue(res.in_numerator)
        self.assertFalse(res.is_gap_in_care)

    def test_fobt_numerator(self):
        pt = PatientRecord(
            patient_id="PT-FOBT",
            birth_date="1965-02-20",
            gender="female",
            encounters=[EncounterRecord("ambulatory", "99213", "CPT", "2026-02-01")],
            observations=[ObservationRecord("14563-1", "LOINC", "Negative", "2026-05-10")],
        )
        res = CQLEquivalentEngine.evaluate_cms130v11(pt, self.mp)
        self.assertTrue(res.in_numerator)

    def test_screening_gap(self):
        pt = PatientRecord(
            patient_id="PT-NIL-SCREEN",
            birth_date="1965-02-20",
            gender="female",
            encounters=[EncounterRecord("ambulatory", "99213", "CPT", "2026-02-01")],
        )
        res = CQLEquivalentEngine.evaluate_cms130v11(pt, self.mp)
        self.assertTrue(res.in_denominator)
        self.assertFalse(res.in_numerator)
        self.assertTrue(res.is_gap_in_care)

    def test_total_colectomy_exclusion(self):
        pt = PatientRecord(
            patient_id="PT-COLECTOMY",
            birth_date="1960-01-01",
            gender="female",
            encounters=[EncounterRecord("ambulatory", "99213", "CPT", "2026-01-10")],
            procedures=[ProcedureRecord("44150", "CPT", "2020-06-01")],
        )
        res = CQLEquivalentEngine.evaluate_cms130v11(pt, self.mp)
        self.assertTrue(res.in_initial_population)
        self.assertTrue(res.in_denominator_exclusion)
        self.assertFalse(res.in_numerator)


class TestCMS122DiabetesHbA1c(unittest.TestCase):
    """Test CMS122v11 Diabetes HbA1c Poor Control measure."""

    def setUp(self):
        self.mp = MeasurementPeriod("2026-01-01", "2026-12-31")

    def test_non_diabetic_excluded(self):
        pt = PatientRecord(
            patient_id="PT-NON-DM",
            birth_date="1970-01-01",
            gender="male",
            encounters=[EncounterRecord("ambulatory", "99213", "CPT", "2026-01-10")],
        )
        res = CQLEquivalentEngine.evaluate_cms122v11(pt, self.mp)
        self.assertFalse(res.in_initial_population)

    def test_controlled_hba1c(self):
        pt = PatientRecord(
            patient_id="PT-DM-GOOD",
            birth_date="1970-01-01",
            gender="male",
            conditions=[ConditionRecord("E11.9", "ICD-10-CM", "2019-01-01")],
            observations=[ObservationRecord("4548-4", "LOINC", 7.1, "2026-06-01")],
        )
        res = CQLEquivalentEngine.evaluate_cms122v11(pt, self.mp)
        self.assertTrue(res.in_initial_population)
        self.assertFalse(res.in_numerator)  # Not in numerator means NOT poor control (good)
        self.assertFalse(res.is_gap_in_care)

    def test_poor_control_high_hba1c(self):
        pt = PatientRecord(
            patient_id="PT-DM-POOR",
            birth_date="1970-01-01",
            gender="male",
            conditions=[ConditionRecord("E11.65", "ICD-10-CM", "2019-01-01")],
            observations=[ObservationRecord("4548-4", "LOINC", 10.5, "2026-06-01")],
        )
        res = CQLEquivalentEngine.evaluate_cms122v11(pt, self.mp)
        self.assertTrue(res.in_numerator)  # Numerator met for poor control
        self.assertTrue(res.is_gap_in_care)

    def test_missing_hba1c_treated_as_poor_control(self):
        pt = PatientRecord(
            patient_id="PT-DM-NO-TEST",
            birth_date="1970-01-01",
            gender="female",
            conditions=[ConditionRecord("E11.9", "ICD-10-CM", "2019-01-01")],
        )
        res = CQLEquivalentEngine.evaluate_cms122v11(pt, self.mp)
        self.assertTrue(res.in_numerator)
        self.assertTrue(res.is_gap_in_care)


class TestCMS125BreastCancerScreening(unittest.TestCase):
    """Test CMS125v11 Breast Cancer Screening measure."""

    def setUp(self):
        self.mp = MeasurementPeriod("2026-01-01", "2026-12-31")

    def test_male_excluded(self):
        pt = PatientRecord(
            patient_id="PT-MALE",
            birth_date="1965-01-01",
            gender="male",
            encounters=[EncounterRecord("ambulatory", "99213", "CPT", "2026-01-10")],
        )
        res = CQLEquivalentEngine.evaluate_cms125v11(pt, self.mp)
        self.assertFalse(res.in_initial_population)

    def test_compliant_mammogram(self):
        pt = PatientRecord(
            patient_id="PT-FEMALE-MAMMO",
            birth_date="1965-05-12",  # Age 61
            gender="female",
            procedures=[ProcedureRecord("77067", "CPT", "2025-08-10")],
        )
        res = CQLEquivalentEngine.evaluate_cms125v11(pt, self.mp)
        self.assertTrue(res.in_initial_population)
        self.assertTrue(res.in_numerator)

    def test_mastectomy_exclusion(self):
        pt = PatientRecord(
            patient_id="PT-MASTECTOMY",
            birth_date="1965-05-12",
            gender="female",
            procedures=[ProcedureRecord("19300", "CPT", "2020-01-15")],
        )
        res = CQLEquivalentEngine.evaluate_cms125v11(pt, self.mp)
        self.assertTrue(res.in_denominator_exclusion)


class TestCMS165BloodPressure(unittest.TestCase):
    """Test CMS165v11 Controlling High Blood Pressure measure."""

    def setUp(self):
        self.mp = MeasurementPeriod("2026-01-01", "2026-12-31")

    def test_controlled_bp(self):
        pt = PatientRecord(
            patient_id="PT-HTN-CONTROLLED",
            birth_date="1960-01-01",
            gender="male",
            conditions=[ConditionRecord("I10", "ICD-10-CM", "2020-01-01")],
            observations=[
                ObservationRecord("8480-6", "LOINC", 124.0, "2026-05-10"),
                ObservationRecord("8462-4", "LOINC", 78.0, "2026-05-10"),
            ]
        )
        res = CQLEquivalentEngine.evaluate_cms165v11(pt, self.mp)
        self.assertTrue(res.in_initial_population)
        self.assertTrue(res.in_numerator)
        self.assertFalse(res.is_gap_in_care)

    def test_uncontrolled_bp(self):
        pt = PatientRecord(
            patient_id="PT-HTN-UNCONTROLLED",
            birth_date="1960-01-01",
            gender="male",
            conditions=[ConditionRecord("I10", "ICD-10-CM", "2020-01-01")],
            observations=[
                ObservationRecord("8480-6", "LOINC", 154.0, "2026-05-10"),
                ObservationRecord("8462-4", "LOINC", 94.0, "2026-05-10"),
            ]
        )
        res = CQLEquivalentEngine.evaluate_cms165v11(pt, self.mp)
        self.assertFalse(res.in_numerator)
        self.assertTrue(res.is_gap_in_care)


class TestPopulationCohortScoring(unittest.TestCase):
    """Test cohort aggregation and parser."""

    def test_cohort_evaluation_rate(self):
        pts = [
            PatientRecord("PT-1", "1960-01-01", "male", encounters=[EncounterRecord("amb", "99213", "CPT", "2026-01-01")], procedures=[ProcedureRecord("45378", "CPT", "2023-01-01")]),
            PatientRecord("PT-2", "1962-01-01", "female", encounters=[EncounterRecord("amb", "99213", "CPT", "2026-01-01")]), # Gap
        ]
        score = CQLEquivalentEngine.evaluate_population_cohort("CMS130v11", pts)
        self.assertEqual(score.denominator_count, 2)
        self.assertEqual(score.numerator_count, 1)
        self.assertEqual(score.effective_denominator_count, 2)
        self.assertAlmostEqual(score.performance_rate_pct, 50.0)

    def test_parse_patient_dict(self):
        raw = {
            "patient_id": "PT-DICT-01",
            "birth_date": "1975-03-20",
            "gender": "female",
            "encounters": [{"code": "99214", "period_start": "2026-02-15"}],
            "conditions": [{"code": "E11.9", "onset_date": "2021-01-01"}],
            "observations": [{"code": "4548-4", "value": 6.8, "date": "2026-02-15"}],
            "medications": [{"code": "metformin", "authored_date": "2026-02-15"}]
        }
        pt = parse_patient_dict(raw)
        self.assertEqual(pt.patient_id, "PT-DICT-01")
        self.assertEqual(len(pt.encounters), 1)
        self.assertEqual(len(pt.conditions), 1)
        self.assertEqual(len(pt.observations), 1)
        self.assertEqual(len(pt.medications), 1)

    def test_json_export_structure(self):
        pts = [PatientRecord("PT-EXPORT", "1970-01-01", "female")]
        score = CQLEquivalentEngine.evaluate_population_cohort("CMS130v11", pts)
        d = score.to_dict()
        self.assertIn("measure_id", d)
        self.assertIn("counts", d)
        self.assertIn("performance_rate_pct", d)
        self.assertIn("patient_evaluations", d)


if __name__ == "__main__":
    unittest.main()
