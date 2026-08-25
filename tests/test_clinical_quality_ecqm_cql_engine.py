"""
End-to-End Integration and Measure Conformance Tests for eCQM CQL Engine
"""

import unittest
import os
import sys

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

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


class TestClinicalQualityECQMCQLEngineFull(unittest.TestCase):

    def test_cms68_medication_documentation(self):
        pt_with_meds = PatientRecord(
            patient_id="PT-MEDS-OK",
            birth_date="1980-01-01",
            gender="female",
            encounters=[EncounterRecord("ambulatory", "99213", "CPT", "2026-03-01")],
            medications=[MedicationRecord("atorvastatin", "RxNorm", "2026-03-01")]
        )
        pt_no_meds = PatientRecord(
            patient_id="PT-MEDS-NONE",
            birth_date="1980-01-01",
            gender="male",
            encounters=[EncounterRecord("ambulatory", "99213", "CPT", "2026-03-01")],
        )
        mp = MeasurementPeriod()
        res_ok = CQLEquivalentEngine.evaluate_cms68v12(pt_with_meds, mp)
        res_none = CQLEquivalentEngine.evaluate_cms68v12(pt_no_meds, mp)

        self.assertTrue(res_ok.in_numerator)
        self.assertFalse(res_none.in_numerator)
        self.assertTrue(res_none.is_gap_in_care)

    def test_multi_measure_cohort_pipeline(self):
        cohort_raw = [
            {
                "patient_id": "PT-MULTI-1",
                "birth_date": "1960-01-01",
                "gender": "male",
                "encounters": [{"code": "99213", "period_start": "2026-04-01"}],
                "conditions": [{"code": "I10", "onset_date": "2020-01-01"}],
                "observations": [
                    {"code": "8480-6", "value": 118.0, "date": "2026-04-01"},
                    {"code": "8462-4", "value": 76.0, "date": "2026-04-01"}
                ],
                "procedures": [{"code": "45378", "performed_date": "2024-01-01"}],
                "medications": [{"code": "amlodipine", "authored_date": "2026-04-01"}]
            }
        ]
        patients = [parse_patient_dict(p) for p in cohort_raw]
        mp = MeasurementPeriod()

        score_colo = CQLEquivalentEngine.evaluate_population_cohort("CMS130v11", patients, mp)
        score_bp = CQLEquivalentEngine.evaluate_population_cohort("CMS165v11", patients, mp)
        score_meds = CQLEquivalentEngine.evaluate_population_cohort("CMS68v12", patients, mp)

        self.assertEqual(score_colo.numerator_count, 1)
        self.assertEqual(score_bp.numerator_count, 1)
        self.assertEqual(score_meds.numerator_count, 1)

    def test_hospice_exclusion_across_measures(self):
        pt_hospice = PatientRecord(
            patient_id="PT-HOSPICE",
            birth_date="1960-01-01",
            gender="female",
            conditions=[
                ConditionRecord("I10", "ICD-10-CM", "2020-01-01", "active"),
                ConditionRecord("Z51.5", "ICD-10-CM", "2026-01-01", "active"),
            ],
            encounters=[EncounterRecord("ambulatory", "99213", "CPT", "2026-01-01")]
        )
        mp = MeasurementPeriod()
        res_bp = CQLEquivalentEngine.evaluate_cms165v11(pt_hospice, mp)
        self.assertTrue(res_bp.in_denominator_exclusion)

    def test_empty_cohort(self):
        score = CQLEquivalentEngine.evaluate_population_cohort("CMS130v11", [])
        self.assertEqual(score.initial_population_count, 0)
        self.assertEqual(score.performance_rate_pct, 0.0)


if __name__ == "__main__":
    unittest.main()
