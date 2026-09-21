"""Simplified clinical quality measure reference evaluator.

The public API retains historical class and measure identifiers for compatibility.
This package does not parse or execute Clinical Quality Language (CQL).
"""

from .models import (
    MeasurePopulation,
    QualityMeasureType,
    QualityMeasureImprovement,
    Coding,
    ObservationRecord,
    ConditionRecord,
    ProcedureRecord,
    EncounterRecord,
    MedicationRecord,
    PatientRecord,
    MeasurementPeriod,
    PatientMeasureResult,
    PopulationMeasureScore,
)
from .engine import (
    CQLExpressionEvaluator,
    CQLEquivalentEngine,
    parse_patient_dict,
)

__all__ = [
    "MeasurePopulation",
    "QualityMeasureType",
    "QualityMeasureImprovement",
    "Coding",
    "ObservationRecord",
    "ConditionRecord",
    "ProcedureRecord",
    "EncounterRecord",
    "MedicationRecord",
    "PatientRecord",
    "MeasurementPeriod",
    "PatientMeasureResult",
    "PopulationMeasureScore",
    "CQLExpressionEvaluator",
    "CQLEquivalentEngine",
    "parse_patient_dict",
]
