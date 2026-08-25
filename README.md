# Clinical Quality eCQM & CQL Execution Engine

> **Electronic Clinical Quality Measure (eCQM) & Clinical Quality Language (CQL) Processing Framework**  
> Reference Standards: **HL7 CQL Release 1.5, CMS / ONC eCQM Quality Measure Specifications, US Core FHIR IG**

---

## Overview

The **Clinical Quality eCQM & CQL Engine** is a deterministic evaluation platform designed to calculate CMS/ONC electronic Clinical Quality Measures (eCQMs) against electronic health records (EHR) and FHIR data models.

It provides native evaluation of standard CMS quality measures, population criteria partitioning (**Initial Population**, **Denominator**, **Denominator Exclusions/Exceptions**, **Numerator**, **Numerator Exclusions**), gap-in-care analytics, and temporal logic predicates.

```
                    +----------------------------------------------+
                    |       Patient EHR / FHIR Resource Model      |
                    |  (Encounters, Conditions, Labs, Procedures)  |
                    +----------------------------------------------+
                                           |
                                           v
                    +----------------------------------------------+
                    |        eCQM / CQL Measure Evaluator          |
                    |  - Standard Clinical ValueSet Matching       |
                    |  - CQL Lookback & Interval Temporal Logic    |
                    |  - Population Criteria & Stratification      |
                    +----------------------------------------------+
                                           |
                                           v
                    +----------------------------------------------+
                    |           Quality Measure Dossier            |
                    |  - Measure Performance Rate (%)              |
                    |  - Gaps in Care Identification               |
                    |  - Patient-Level Criteria Rationale Trace    |
                    +----------------------------------------------+
```

---

## Supported eCQM Measure Specifications

| Measure ID | Measure Title | Target Population | Numerator Criteria | Improvement |
| :--- | :--- | :--- | :--- | :---: |
| **CMS130v11** | Colorectal Cancer Screening | Patients 45–75 with visit | FOBT (1y), FIT-DNA (3y), Sigmoidoscopy (5y), CT (5y), Colonoscopy (10y) | Higher is better |
| **CMS122v11** | Diabetes: HbA1c Poor Control (>9.0%) | Patients 18–75 with diabetes | Most recent HbA1c > 9.0% or missing during measurement period | Lower is better (Inverse) |
| **CMS125v11** | Breast Cancer Screening | Females 52–74 | Mammogram within 27 months lookback | Higher is better |
| **CMS165v11** | Controlling High Blood Pressure | Patients 18–85 with hypertension | Most recent BP controlled (< 140/90 mmHg) | Higher is better |
| **CMS68v12** | Current Medication Documentation | Patients ≥ 18 with encounter | Documented active medication list in medical record | Higher is better |

---

## Population Logic & Mathematical Model

$$\text{Effective Denominator} = \text{Denominator} - \text{Denominator Exclusions} - \text{Denominator Exceptions}$$

$$\text{Performance Rate (\%)} = \frac{\text{Numerator} - \text{Numerator Exclusions}}{\text{Effective Denominator}} \times 100\%$$

- **Gap in Care**: Patients who satisfy the Denominator criteria but fail the Numerator criteria without meeting an Exclusion or Exception.

---

## Command-Line Interface (CLI)

### Demonstration on Sample Cohort
```bash
python cli.py --demo --measure CMS130v11
```

### Evaluate Diabetes Measure (CMS122v11) with JSON Export
```bash
python cli.py --measure CMS122v11 --json
```

### Interactive Patient Evaluation
```bash
python cli.py --interactive
```

### List Supported Quality Measures
```bash
python cli.py --list-measures
```

### Ingest Custom Cohort File
```bash
python cli.py --file cohort_dataset.json --measure CMS165v11
```

---

## Python API Usage

```python
from ecqm_cql_engine import (
    CQLEquivalentEngine,
    PatientRecord,
    EncounterRecord,
    ConditionRecord,
    ObservationRecord,
    ProcedureRecord,
    MeasurementPeriod,
)

patient = PatientRecord(
    patient_id="PT-101",
    birth_date="1962-04-15",
    gender="male",
    encounters=[EncounterRecord("ambulatory", "99213", "CPT", "2026-03-01")],
    procedures=[ProcedureRecord("45378", "CPT", "2023-08-10")],  # Colonoscopy
)

mp = MeasurementPeriod("2026-01-01", "2026-12-31")
res = CQLEquivalentEngine.evaluate_cms130v11(patient, mp)

print(f"In IPP: {res.in_initial_population}")
print(f"In Numerator: {res.in_numerator}")
print(f"Gap in Care: {res.is_gap_in_care}")
print(f"Rationale: {res.rationale}")
```

---

## Test Suite Execution

Run the comprehensive test suite verifying CQL temporal predicates, clinical coding, population criteria, and edge cases:

```bash
python -m unittest discover -s tests -v
```

```
test_cms68_medication_documentation ... ok
test_controlled_hba1c ... ok
test_missing_hba1c_treated_as_poor_control ... ok
test_compliant_mammogram ... ok
test_colonoscopy_numerator ... ok
test_controlled_bp ... ok
test_date_in_interval_boundary ... ok
test_lookback_years ... ok
test_cohort_evaluation_rate ... ok
----------------------------------------------------------------------
Ran 26 tests in 0.002s

OK
```

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
