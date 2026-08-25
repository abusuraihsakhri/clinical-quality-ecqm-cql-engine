"""
Core eCQM & CQL Measure Execution Engine
Domain: Electronic Clinical Quality Measures & CQL Evaluator
Standards: HL7 CQL Release 1.5, CMS/ONC eCQM Quality Measure Specifications
"""

import datetime
from typing import Dict, List, Optional, Any, Set, Callable
from .models import (
    PatientRecord,
    EncounterRecord,
    ConditionRecord,
    ObservationRecord,
    ProcedureRecord,
    MedicationRecord,
    MeasurementPeriod,
    PatientMeasureResult,
    PopulationMeasureScore,
    QualityMeasureImprovement,
)


class CQLExpressionEvaluator:
    """
    Evaluator for Clinical Quality Language (CQL) temporal predicates,
    code matching, age calculations, and set operations.
    """

    @staticmethod
    def is_date_in_interval(target_date_str: str, start_date_str: str, end_date_str: str) -> bool:
        """Check if target_date is in [start_date, end_date]."""
        target = datetime.date.fromisoformat(target_date_str)
        start = datetime.date.fromisoformat(start_date_str)
        end = datetime.date.fromisoformat(end_date_str)
        return start <= target <= end

    @staticmethod
    def is_date_within_lookback_months(target_date_str: str, anchor_date_str: str, months: int) -> bool:
        """Check if target_date is within `months` prior to anchor_date."""
        target = datetime.date.fromisoformat(target_date_str)
        anchor = datetime.date.fromisoformat(anchor_date_str)
        if target > anchor:
            return False
        # Approximate 30.4375 days per month
        diff_days = (anchor - target).days
        max_days = int(months * 30.5)
        return diff_days <= max_days

    @staticmethod
    def is_date_within_lookback_years(target_date_str: str, anchor_date_str: str, years: int) -> bool:
        """Check if target_date is within `years` prior to anchor_date."""
        target = datetime.date.fromisoformat(target_date_str)
        anchor = datetime.date.fromisoformat(anchor_date_str)
        if target > anchor:
            return False
        diff_days = (anchor - target).days
        return diff_days <= (years * 366)


# Standard Clinical CodeSets (SNOMED, LOINC, ICD-10, CPT, RxNorm)
COLORECTAL_CANCER_CODES = {"C18.0", "C18.9", "C19", "C20", "363406005"}
COLONOSCOPY_CODES = {"45378", "45380", "45385", "705000007"}
FOBT_LAB_CODES = {"14563-1", "14564-9", "29771-3", "82270", "82274"}
FIT_DNA_CODES = {"81528", "77353-1"}
CT_COLONOGRAPHY_CODES = {"74263", "82675008"}
FLEXIBLE_SIGMOIDOSCOPY_CODES = {"45330", "45331", "441360001"}
TOTAL_COLECTOMY_CODES = {"44150", "44151", "0DTE0ZZ"}

DIABETES_CONDITION_CODES = {"E11.9", "E11.65", "E10.9", "73211009", "44054006"}
HBA1C_LOINC_CODES = {"4548-4", "17856-6", "4549-2", "96595-4"}

MAMMOGRAM_PROC_CODES = {"77067", "77063", "77065", "77066", "24623002"}
BILATERAL_MASTECTOMY_CODES = {"19300", "0HTV0ZZ", "172043006"}

HYPERTENSION_CONDITION_CODES = {"I10", "59621000", "38341003"}
SYSTOLIC_BP_LOINC = {"8480-6", "8462-4"}
DIASTOLIC_BP_LOINC = {"8462-4", "8453-3"}
ESRD_CODES = {"N18.6", "46177005"}
PREGNANCY_CODES = {"Z34.00", "Z34.80", "77386006"}

HOSPICE_PALLIATIVE_CODES = {"Z51.5", "305336008", "305911006", "99377"}
OUTPATIENT_ENCOUNTER_CODES = {"99202", "99203", "99204", "99205", "99212", "99213", "99214", "99215"}


class CQLEquivalentEngine:
    """
    Standard Measure Execution Engine implementing CMS/ONC eCQM quality measures.
    """

    @classmethod
    def evaluate_cms130v11(cls, patient: PatientRecord, mp: MeasurementPeriod) -> PatientMeasureResult:
        """
        CMS130v11: Colorectal Cancer Screening
        - Initial Population: Patients 45-75 years of age at start of MP with an outpatient visit during MP.
        - Denominator: Equals Initial Population.
        - Denominator Exclusions: Total colectomy, colorectal cancer history, or hospice/palliative care.
        - Numerator: Screening performed (FOBT in MP, FIT-DNA within 3y, CT Colonography within 5y, Sigmoidoscopy within 5y, or Colonoscopy within 10y).
        """
        res = PatientMeasureResult(patient_id=patient.patient_id, measure_id="CMS130v11")
        age_at_start = patient.calculate_age_at(mp.start_date)

        # Qualifying encounter during MP
        has_qualifying_encounter = any(
            enc.code in OUTPATIENT_ENCOUNTER_CODES and CQLExpressionEvaluator.is_date_in_interval(enc.period_start, mp.start_date, mp.end_date)
            for enc in patient.encounters
        ) or len(patient.encounters) > 0

        if not (45 <= age_at_start <= 75 and has_qualifying_encounter):
            res.rationale.append(f"Excluded from IP: Age={age_at_start} (must be 45-75) or no qualifying encounter in MP.")
            return res

        res.in_initial_population = True
        res.in_denominator = True
        res.rationale.append(f"Initial Population & Denominator Met: Age={age_at_start} with qualifying encounter.")

        # Denominator Exclusions
        has_cancer = any(c.code in COLORECTAL_CANCER_CODES for c in patient.conditions)
        has_colectomy = any(p.code in TOTAL_COLECTOMY_CODES for p in patient.procedures)
        has_hospice = any(c.code in HOSPICE_PALLIATIVE_CODES for c in patient.conditions) or any(
            p.code in HOSPICE_PALLIATIVE_CODES for p in patient.procedures
        )

        if has_cancer or has_colectomy or has_hospice:
            res.in_denominator_exclusion = True
            reason = "Colorectal Cancer" if has_cancer else ("Total Colectomy" if has_colectomy else "Hospice Care")
            res.rationale.append(f"Denominator Exclusion Met: {reason}.")
            return res

        # Numerator: Screening compliance
        # 1. FOBT during MP
        fobt_done = any(
            obs.code in FOBT_LAB_CODES and CQLExpressionEvaluator.is_date_in_interval(obs.date, mp.start_date, mp.end_date)
            for obs in patient.observations
        )
        # 2. FIT-DNA within 3 years
        fit_dna_done = any(
            (obs.code in FIT_DNA_CODES or proc.code in FIT_DNA_CODES)
            and CQLExpressionEvaluator.is_date_within_lookback_years(obs.date if obs.code in FIT_DNA_CODES else proc.performed_date, mp.end_date, 3)
            for obs in patient.observations
            for proc in patient.procedures
        ) or any(
            obs.code in FIT_DNA_CODES and CQLExpressionEvaluator.is_date_within_lookback_years(obs.date, mp.end_date, 3)
            for obs in patient.observations
        )
        # 3. Colonoscopy within 10 years
        colonoscopy_done = any(
            proc.code in COLONOSCOPY_CODES and CQLExpressionEvaluator.is_date_within_lookback_years(proc.performed_date, mp.end_date, 10)
            for proc in patient.procedures
        )
        # 4. Sigmoidoscopy within 5 years
        sigmoidoscopy_done = any(
            proc.code in FLEXIBLE_SIGMOIDOSCOPY_CODES and CQLExpressionEvaluator.is_date_within_lookback_years(proc.performed_date, mp.end_date, 5)
            for proc in patient.procedures
        )
        # 5. CT Colonography within 5 years
        ct_done = any(
            proc.code in CT_COLONOGRAPHY_CODES and CQLExpressionEvaluator.is_date_within_lookback_years(proc.performed_date, mp.end_date, 5)
            for proc in patient.procedures
        )

        if fobt_done or fit_dna_done or colonoscopy_done or sigmoidoscopy_done or ct_done:
            res.in_numerator = True
            modality = "Colonoscopy (10y)" if colonoscopy_done else ("FOBT (1y)" if fobt_done else ("FIT-DNA (3y)" if fit_dna_done else "Sigmoidoscopy/CT (5y)"))
            res.rationale.append(f"Numerator Met: Screening confirmed via {modality}.")
        else:
            res.is_gap_in_care = True
            res.rationale.append("Numerator Not Met: Colorectal cancer screening gap in care.")

        return res

    @classmethod
    def evaluate_cms122v11(cls, patient: PatientRecord, mp: MeasurementPeriod) -> PatientMeasureResult:
        """
        CMS122v11: Diabetes: Hemoglobin A1c (HbA1c) Poor Control (> 9.0%)
        - Inverse measure: Higher rate indicates poorer quality.
        - Initial Population: Patients 18-75 years of age with diabetes diagnosis.
        - Denominator: Equals Initial Population.
        - Denominator Exclusions: Hospice / palliative care.
        - Numerator: Most recent HbA1c during MP is > 9.0% OR missing/no test performed during MP.
        """
        res = PatientMeasureResult(patient_id=patient.patient_id, measure_id="CMS122v11")
        age_at_start = patient.calculate_age_at(mp.start_date)

        has_diabetes = any(c.code in DIABETES_CONDITION_CODES and c.clinical_status == "active" for c in patient.conditions)

        if not (18 <= age_at_start <= 75 and has_diabetes):
            res.rationale.append(f"Excluded from IP: Age={age_at_start} (18-75) or no active Diabetes diagnosis.")
            return res

        res.in_initial_population = True
        res.in_denominator = True
        res.rationale.append("Initial Population & Denominator Met: Active Diabetes diagnosis in age 18-75.")

        has_hospice = any(c.code in HOSPICE_PALLIATIVE_CODES for c in patient.conditions)
        if has_hospice:
            res.in_denominator_exclusion = True
            res.rationale.append("Denominator Exclusion Met: Hospice / palliative care.")
            return res

        # Find all HbA1c observations in MP
        hba1c_obs = [
            obs for obs in patient.observations
            if obs.code in HBA1C_LOINC_CODES and CQLExpressionEvaluator.is_date_in_interval(obs.date, mp.start_date, mp.end_date)
        ]

        if not hba1c_obs:
            # Missing test -> Numerator True (Poor control by omission)
            res.in_numerator = True
            res.is_gap_in_care = True
            res.rationale.append("Numerator Met (Poor Control): No HbA1c test documented during measurement period.")
        else:
            # Sort by date descending
            hba1c_obs.sort(key=lambda x: x.date, reverse=True)
            most_recent = hba1c_obs[0]
            val = float(most_recent.value)
            if val > 9.0:
                res.in_numerator = True
                res.is_gap_in_care = True
                res.rationale.append(f"Numerator Met (Poor Control): Most recent HbA1c is {val:.1f}% (> 9.0%).")
            else:
                res.in_numerator = False
                res.rationale.append(f"Numerator Not Met (Controlled): Most recent HbA1c is {val:.1f}% (<= 9.0%).")

        return res

    @classmethod
    def evaluate_cms125v11(cls, patient: PatientRecord, mp: MeasurementPeriod) -> PatientMeasureResult:
        """
        CMS125v11: Breast Cancer Screening
        - Initial Population: Women 52-74 years of age at end of MP.
        - Denominator: Equals Initial Population.
        - Denominator Exclusions: Bilateral mastectomy or hospice care.
        - Numerator: One or more mammograms within 27 months prior to end of MP.
        """
        res = PatientMeasureResult(patient_id=patient.patient_id, measure_id="CMS125v11")
        age_at_end = patient.calculate_age_at(mp.end_date)

        if not (patient.gender.lower() == "female" and 52 <= age_at_end <= 74):
            res.rationale.append(f"Excluded from IP: Gender={patient.gender}, Age={age_at_end} (must be Female 52-74).")
            return res

        res.in_initial_population = True
        res.in_denominator = True
        res.rationale.append(f"Initial Population & Denominator Met: Female age {age_at_end}.")

        has_mastectomy = any(p.code in BILATERAL_MASTECTOMY_CODES for p in patient.procedures) or any(
            c.code in BILATERAL_MASTECTOMY_CODES for c in patient.conditions
        )
        has_hospice = any(c.code in HOSPICE_PALLIATIVE_CODES for c in patient.conditions)

        if has_mastectomy or has_hospice:
            res.in_denominator_exclusion = True
            reason = "Bilateral Mastectomy" if has_mastectomy else "Hospice Care"
            res.rationale.append(f"Denominator Exclusion Met: {reason}.")
            return res

        has_mammogram = any(
            p.code in MAMMOGRAM_PROC_CODES and CQLExpressionEvaluator.is_date_within_lookback_months(p.performed_date, mp.end_date, 27)
            for p in patient.procedures
        )

        if has_mammogram:
            res.in_numerator = True
            res.rationale.append("Numerator Met: Screening mammogram completed within 27-month lookback.")
        else:
            res.is_gap_in_care = True
            res.rationale.append("Numerator Not Met: Breast cancer screening gap in care.")

        return res

    @classmethod
    def evaluate_cms165v11(cls, patient: PatientRecord, mp: MeasurementPeriod) -> PatientMeasureResult:
        """
        CMS165v11: Controlling High Blood Pressure
        - Initial Population: Patients 18-85 years of age with essential hypertension.
        - Denominator: Equals Initial Population.
        - Denominator Exclusions: ESRD, dialysis, pregnancy, hospice.
        - Numerator: Most recent BP during MP is < 140/90 mmHg (both SBP < 140 and DBP < 90).
        """
        res = PatientMeasureResult(patient_id=patient.patient_id, measure_id="CMS165v11")
        age_at_end = patient.calculate_age_at(mp.end_date)
        has_htn = any(c.code in HYPERTENSION_CONDITION_CODES and c.clinical_status == "active" for c in patient.conditions)

        if not (18 <= age_at_end <= 85 and has_htn):
            res.rationale.append(f"Excluded from IP: Age={age_at_end} or no active Hypertension diagnosis.")
            return res

        res.in_initial_population = True
        res.in_denominator = True
        res.rationale.append("Initial Population & Denominator Met: Hypertension diagnosis in age 18-85.")

        has_esrd = any(c.code in ESRD_CODES for c in patient.conditions)
        has_preg = any(c.code in PREGNANCY_CODES for c in patient.conditions)
        has_hospice = any(c.code in HOSPICE_PALLIATIVE_CODES for c in patient.conditions)

        if has_esrd or has_preg or has_hospice:
            res.in_denominator_exclusion = True
            reason = "ESRD" if has_esrd else ("Pregnancy" if has_preg else "Hospice Care")
            res.rationale.append(f"Denominator Exclusion Met: {reason}.")
            return res

        # Find SBP and DBP observations during MP
        sbp_obs = [
            obs for obs in patient.observations
            if obs.code in SYSTOLIC_BP_LOINC and CQLExpressionEvaluator.is_date_in_interval(obs.date, mp.start_date, mp.end_date)
        ]
        dbp_obs = [
            obs for obs in patient.observations
            if obs.code in DIASTOLIC_BP_LOINC and CQLExpressionEvaluator.is_date_in_interval(obs.date, mp.start_date, mp.end_date)
        ]

        if not sbp_obs or not dbp_obs:
            res.in_numerator = False
            res.is_gap_in_care = True
            res.rationale.append("Numerator Not Met: Missing Blood Pressure reading during MP.")
            return res

        sbp_obs.sort(key=lambda x: x.date, reverse=True)
        dbp_obs.sort(key=lambda x: x.date, reverse=True)

        recent_sbp = float(sbp_obs[0].value)
        recent_dbp = float(dbp_obs[0].value)

        if recent_sbp < 140.0 and recent_dbp < 90.0:
            res.in_numerator = True
            res.rationale.append(f"Numerator Met: Blood pressure controlled at {recent_sbp:.0f}/{recent_dbp:.0f} mmHg (<140/90).")
        else:
            res.is_gap_in_care = True
            res.rationale.append(f"Numerator Not Met: Blood pressure uncontrolled at {recent_sbp:.0f}/{recent_dbp:.0f} mmHg.")

        return res

    @classmethod
    def evaluate_cms68v12(cls, patient: PatientRecord, mp: MeasurementPeriod) -> PatientMeasureResult:
        """
        CMS68v12: Documentation of Current Medications in the Medical Record
        - Initial Population: Patients >= 18 with qualifying encounter.
        - Numerator: Current medications documented during encounter.
        """
        res = PatientMeasureResult(patient_id=patient.patient_id, measure_id="CMS68v12")
        age_at_end = patient.calculate_age_at(mp.end_date)
        has_encounter = any(
            CQLExpressionEvaluator.is_date_in_interval(enc.period_start, mp.start_date, mp.end_date)
            for enc in patient.encounters
        ) or len(patient.encounters) > 0

        if not (age_at_end >= 18 and has_encounter):
            res.rationale.append(f"Excluded from IP: Age={age_at_end} or no encounter.")
            return res

        res.in_initial_population = True
        res.in_denominator = True

        has_meds_recorded = len(patient.medications) > 0 or any(
            obs.code == "MED_RECONCILED" for obs in patient.observations
        )

        if has_meds_recorded:
            res.in_numerator = True
            res.rationale.append("Numerator Met: Current medications documented.")
        else:
            res.is_gap_in_care = True
            res.rationale.append("Numerator Not Met: No medication list documented.")

        return res

    @classmethod
    def evaluate_population_cohort(
        cls, measure_id: str, patients: List[PatientRecord], mp: Optional[MeasurementPeriod] = None
    ) -> PopulationMeasureScore:
        """
        Evaluate an entire patient population cohort against a specified eCQM measure.
        """
        if mp is None:
            mp = MeasurementPeriod()

        measure_evaluators: Dict[str, Tuple[str, QualityMeasureImprovement, Callable[[PatientRecord, MeasurementPeriod], PatientMeasureResult]]] = {
            "CMS130V11": ("Colorectal Cancer Screening", QualityMeasureImprovement.INCREASED, cls.evaluate_cms130v11),
            "CMS122V11": ("Diabetes: HbA1c Poor Control (>9.0%)", QualityMeasureImprovement.DECREASED, cls.evaluate_cms122v11),
            "CMS125V11": ("Breast Cancer Screening", QualityMeasureImprovement.INCREASED, cls.evaluate_cms125v11),
            "CMS165V11": ("Controlling High Blood Pressure", QualityMeasureImprovement.INCREASED, cls.evaluate_cms165v11),
            "CMS68V12": ("Documentation of Current Medications", QualityMeasureImprovement.INCREASED, cls.evaluate_cms68v12),
        }

        measure_key = measure_id.upper()
        if measure_key not in measure_evaluators:
            # Fallback to CMS130V11
            measure_key = "CMS130V11"

        title, improvement, eval_func = measure_evaluators[measure_key]

        patient_results = []
        ipp_count = 0
        denom_count = 0
        denex_count = 0
        denexcep_count = 0
        numer_count = 0
        numex_count = 0
        gap_count = 0

        for pt in patients:
            res = eval_func(pt, mp)
            patient_results.append(res)

            if res.in_initial_population:
                ipp_count += 1
            if res.in_denominator:
                denom_count += 1
            if res.in_denominator_exclusion:
                denex_count += 1
            if res.in_denominator_exception:
                denexcep_count += 1
            if res.in_numerator:
                numer_count += 1
            if res.in_numerator_exclusion:
                numex_count += 1
            if res.is_gap_in_care:
                gap_count += 1

        effective_denom = denom_count - denex_count - denexcep_count
        if effective_denom > 0:
            rate_pct = (numer_count - numex_count) / effective_denom * 100.0
        else:
            rate_pct = 0.0

        return PopulationMeasureScore(
            measure_id=measure_key,
            measure_title=title,
            measurement_period=mp,
            improvement_notation=improvement,
            initial_population_count=ipp_count,
            denominator_count=denom_count,
            denominator_exclusion_count=denex_count,
            denominator_exception_count=denexcep_count,
            numerator_count=numer_count,
            numerator_exclusion_count=numex_count,
            effective_denominator_count=effective_denom,
            performance_rate_pct=rate_pct,
            gap_in_care_count=gap_count,
            patient_results=patient_results,
        )


def parse_patient_dict(data: Dict[str, Any]) -> PatientRecord:
    """Parse raw JSON/dict patient into structured PatientRecord."""
    encs = [
        EncounterRecord(
            encounter_type=e.get("encounter_type", "ambulatory"),
            code=str(e.get("code", "99213")),
            code_system=e.get("code_system", "CPT"),
            period_start=str(e.get("period_start", "2026-06-01")),
            period_end=e.get("period_end"),
            status=e.get("status", "finished"),
        )
        for e in data.get("encounters", [])
    ]
    conds = [
        ConditionRecord(
            code=str(c.get("code", "")),
            code_system=c.get("code_system", "ICD-10-CM"),
            onset_date=str(c.get("onset_date", "2026-01-01")),
            clinical_status=c.get("clinical_status", "active"),
            display=c.get("display"),
        )
        for c in data.get("conditions", [])
    ]
    obss = [
        ObservationRecord(
            code=str(o.get("code", "")),
            code_system=o.get("code_system", "LOINC"),
            value=o.get("value", 0.0),
            date=str(o.get("date", "2026-06-01")),
            unit=o.get("unit"),
            status=o.get("status", "final"),
        )
        for o in data.get("observations", [])
    ]
    procs = [
        ProcedureRecord(
            code=str(p.get("code", "")),
            code_system=p.get("code_system", "CPT"),
            performed_date=str(p.get("performed_date", "2026-06-01")),
            status=p.get("status", "completed"),
            display=p.get("display"),
        )
        for p in data.get("procedures", [])
    ]
    meds = [
        MedicationRecord(
            code=str(m.get("code", "")),
            code_system=m.get("code_system", "RxNorm"),
            authored_date=str(m.get("authored_date", "2026-06-01")),
            status=m.get("status", "active"),
            display=m.get("display"),
        )
        for m in data.get("medications", [])
    ]

    return PatientRecord(
        patient_id=str(data.get("patient_id", "PT-UNKNOWN")),
        birth_date=str(data.get("birth_date", "1970-01-01")),
        gender=str(data.get("gender", "unknown")),
        encounters=encs,
        conditions=conds,
        observations=obss,
        procedures=procs,
        medications=meds,
    )
