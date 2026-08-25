"""
Data Models & Definitions for eCQM & CQL Evaluation Engine.
Domain: Electronic Clinical Quality Measures & CQL Evaluator
Standards: HL7 CQL Release 1.5, CMS/ONC eCQM Quality Measure Specifications
"""

import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Union


class MeasurePopulation(str, Enum):
    INITIAL_POPULATION = "initial-population"
    DENOMINATOR = "denominator"
    DENOMINATOR_EXCLUSION = "denominator-exclusion"
    DENOMINATOR_EXCEPTION = "denominator-exception"
    NUMERATOR = "numerator"
    NUMERATOR_EXCLUSION = "numerator-exclusion"


class QualityMeasureType(str, Enum):
    PROPORTION = "proportion"
    RATIO = "ratio"
    CONTINUOUS_VARIABLE = "continuous-variable"
    COHORT = "cohort"


class QualityMeasureImprovement(str, Enum):
    INCREASED = "increased"  # Higher score indicates better quality (e.g. screening)
    DECREASED = "decreased"  # Lower score indicates better quality (e.g. HbA1c > 9% poor control)


@dataclass
class Coding:
    system: str  # e.g., 'http://snomed.info/sct', 'http://loinc.org', 'http://hl7.org/fhir/sid/icd-10-cm'
    code: str
    display: Optional[str] = None


@dataclass
class ObservationRecord:
    code: str
    code_system: str
    value: Union[float, str, bool]
    date: str  # YYYY-MM-DD
    unit: Optional[str] = None
    status: str = "final"


@dataclass
class ConditionRecord:
    code: str
    code_system: str
    onset_date: str  # YYYY-MM-DD
    clinical_status: str = "active"  # active, recurrence, remission, resolved
    display: Optional[str] = None


@dataclass
class ProcedureRecord:
    code: str
    code_system: str
    performed_date: str  # YYYY-MM-DD
    status: str = "completed"
    display: Optional[str] = None


@dataclass
class EncounterRecord:
    encounter_type: str
    code: str
    code_system: str
    period_start: str  # YYYY-MM-DD
    period_end: Optional[str] = None
    status: str = "finished"


@dataclass
class MedicationRecord:
    code: str
    code_system: str
    authored_date: str  # YYYY-MM-DD
    status: str = "active"
    display: Optional[str] = None


@dataclass
class PatientRecord:
    patient_id: str
    birth_date: str  # YYYY-MM-DD
    gender: str  # male, female, other, unknown
    encounters: List[EncounterRecord] = field(default_factory=list)
    conditions: List[ConditionRecord] = field(default_factory=list)
    observations: List[ObservationRecord] = field(default_factory=list)
    procedures: List[ProcedureRecord] = field(default_factory=list)
    medications: List[MedicationRecord] = field(default_factory=list)

    def calculate_age_at(self, target_date_str: str) -> int:
        """Calculate patient age in full years as of target date."""
        birth = datetime.date.fromisoformat(self.birth_date)
        target = datetime.date.fromisoformat(target_date_str)
        return target.year - birth.year - ((target.month, target.day) < (birth.month, birth.day))


@dataclass
class MeasurementPeriod:
    start_date: str = "2026-01-01"
    end_date: str = "2026-12-31"


@dataclass
class PatientMeasureResult:
    patient_id: str
    measure_id: str
    in_initial_population: bool = False
    in_denominator: bool = False
    in_denominator_exclusion: bool = False
    in_denominator_exception: bool = False
    in_numerator: bool = False
    in_numerator_exclusion: bool = False
    is_gap_in_care: bool = False
    rationale: List[str] = field(default_factory=list)


@dataclass
class PopulationMeasureScore:
    measure_id: str
    measure_title: str
    measurement_period: MeasurementPeriod
    improvement_notation: QualityMeasureImprovement
    initial_population_count: int
    denominator_count: int
    denominator_exclusion_count: int
    denominator_exception_count: int
    numerator_count: int
    numerator_exclusion_count: int
    effective_denominator_count: int
    performance_rate_pct: float
    gap_in_care_count: int
    patient_results: List[PatientMeasureResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "measure_id": self.measure_id,
            "measure_title": self.measure_title,
            "measurement_period": {
                "start": self.measurement_period.start_date,
                "end": self.measurement_period.end_date,
            },
            "improvement_notation": self.improvement_notation.value,
            "counts": {
                "initial_population": self.initial_population_count,
                "denominator": self.denominator_count,
                "denominator_exclusions": self.denominator_exclusion_count,
                "denominator_exceptions": self.denominator_exception_count,
                "numerator": self.numerator_count,
                "numerator_exclusions": self.numerator_exclusion_count,
                "effective_denominator": self.effective_denominator_count,
                "gaps_in_care": self.gap_in_care_count,
            },
            "performance_rate_pct": round(self.performance_rate_pct, 2),
            "patient_evaluations": [
                {
                    "patient_id": r.patient_id,
                    "in_initial_population": r.in_initial_population,
                    "in_denominator": r.in_denominator,
                    "in_denominator_exclusion": r.in_denominator_exclusion,
                    "in_denominator_exception": r.in_denominator_exception,
                    "in_numerator": r.in_numerator,
                    "in_numerator_exclusion": r.in_numerator_exclusion,
                    "is_gap_in_care": r.is_gap_in_care,
                    "rationale": r.rationale,
                }
                for r in self.patient_results
            ],
        }
