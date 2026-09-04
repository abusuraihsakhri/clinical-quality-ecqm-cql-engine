# Clinical Quality eCQM / CQL Engine

> **Domain:** Clinical Decision Support & Biomedical Quality Informatics  
> **Reference Guidelines & Standards:** HL7 Clinical Quality Language (CQL) Release 1.5, CMS/ONC eCQM Measure Specifications, NCQA HEDIS® Standards

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![eCQM](https://img.shields.io/badge/eCQM-CMS_Measures_v11--v12-brightgreen.svg)
![CQL](https://img.shields.io/badge/CQL-HL7_Release_1.5-blue.svg)
![Tests](https://img.shields.io/badge/Tests-27_Passed-brightgreen.svg)

</div>

---

## 📖 What It Does

The **Clinical Quality eCQM / CQL Engine** is a deterministic, clinical-grade calculation and gap-in-care evaluation engine designed for healthcare systems, payers, and electronic health record (EHR) platforms. It evaluates patient cohorts and longitudinal clinical records against CMS (Centers for Medicare & Medicaid Services), ONC (Office of the National Coordinator), and NCQA (National Committee for Quality Assurance) electronic Clinical Quality Measures (eCQMs) using standard HL7 Clinical Quality Language (CQL) temporal logic.

Key clinical capabilities include:
- **Deterministic Population Criteria Computation:** Evaluates Initial Patient Population (IPP), Denominators (DENOM), Denominator Exclusions (DENEX), Denominator Exceptions (DENEXCEP), Numerators (NUMER), and Numerator Exclusions (NUMEX).
- **Temporal Predicates & Lookback Windows:** Implements CQL-standard interval arithmetic (e.g., within 27 months, 3 years, 5 years, 10 years, or measurement period boundaries).
- **Standardized Clinical Ontologies:** Ingests and maps SNOMED CT, LOINC, ICD-10-CM, CPT, HCPCS, and RxNorm terminology codes.
- **Actionable Gap-in-Care Analytics:** Pinpoints unclosed screening intervals, missing diagnostic lab orders, elevated biometric thresholds, and unrecorded medication reconciliation.
- **Batch CSV & JSON Processing:** Evaluates longitudinal patient registries with high throughput and exports audit-ready compliance rosters.

---

## 📐 Measure Specifications & Formulations

### Standard Population Metrics Formula

$$\text{Effective Denominator} = \text{Denominator} - \text{Denominator Exclusions} - \text{Denominator Exceptions}$$

$$\text{Performance Rate (\%)} = \left( \frac{\text{Numerator} - \text{Numerator Exclusions}}{\text{Effective Denominator}} \right) \times 100$$

### Supported eCQM Measure Matrix

| Measure ID | Clinical Quality Measure Title | Target Population | Lookback / Temporal Logic | Directionality | Standard Ontologies |
|:---|:---|:---|:---|:---|:---|
| **CMS130v11** | Colorectal Cancer Screening | Age 45–75 at start of MP with outpatient encounter | FOBT (1y), FIT-DNA (3y), Sigmoidoscopy/CT (5y), Colonoscopy (10y) | Higher is better (INCREASED) | CPT, LOINC, ICD-10-CM, SNOMED CT |
| **CMS122v11** | Diabetes: HbA1c Poor Control (> 9.0%) | Age 18–75 with active diabetes diagnosis | Most recent HbA1c > 9.0% or missing test in MP | Lower is better (DECREASED, Inverse) | LOINC, ICD-10-CM, SNOMED CT |
| **CMS125v11** | Breast Cancer Screening | Females age 52–74 at end of MP | Screening mammography within 27 months prior to MP end | Higher is better (INCREASED) | CPT, ICD-10-CM, SNOMED CT |
| **CMS165v11** | Controlling High Blood Pressure | Age 18–85 with essential hypertension | Most recent BP during MP < 140/90 mmHg (both SBP & DBP) | Higher is better (INCREASED) | LOINC, ICD-10-CM |
| **CMS68v12** | Documentation of Current Medications | Age $\ge$ 18 with qualifying encounter | Active medications documented or reconciled during encounter | Higher is better (INCREASED) | CPT, RxNorm, SNOMED CT |

---

## 💻 CLI Quickstart & Usage

### 1. View Supported Measure Specifications
```bash
python cli.py --list-measures
```

### 2. Batch Evaluation via CSV (File I/O)
Process clinical patient cohorts and generate quality measure compliance breakdowns:
```bash
python cli.py batch -i sample.csv -o results.csv --measure CMS130v11
```
Or with long flags:
```bash
python cli.py batch --input sample.csv --output results.csv --measure CMS122v11
```

### 3. Direct Cohort Simulation (Default Cohort)
```bash
python cli.py --measure CMS130v11
```
To output structured JSON:
```bash
python cli.py --measure CMS130v11 --json
```

### 4. Interactive Single-Patient Evaluator
Walk through a clinical case step-by-step with diagnostic and screening inputs:
```bash
python cli.py --interactive
```

---

## 📊 Data Schema (`sample.csv`)

The batch processing interface ingests patient records with standard clinical headers:

```csv
patient_id,birth_date,gender,encounter_code,encounter_date,condition_code,condition_status,condition_date,observation_code,observation_value,observation_date,procedure_code,procedure_date,medication_code,medication_date
PT-1001,1965-04-12,male,99213,2026-03-15,I10,active,2020-01-01,8480-6,128.0,2026-03-15,45378,2022-05-10,lisinopril,2026-03-15
PT-1002,1972-08-25,female,99214,2026-02-10,E11.9,active,2018-09-01,4548-4,7.4,2026-02-10,77067,2025-06-10,metformin,2026-02-10
PT-1003,1958-11-03,female,99203,2026-05-20,E11.65,active,2015-04-10,4548-4,10.2,2026-05-20,,,,
PT-1004,1980-06-18,male,99213,2026-04-15,I10,active,2019-02-10,8480-6,155.0,2026-04-15,,,amlodipine,2026-04-15
PT-1005,1968-12-05,female,99214,2026-03-22,C18.9,active,2022-01-15,,,,,19300,2021-08-10,tamoxifen,2026-03-22
PT-1006,1995-02-14,male,99212,2026-01-10,,,,,,,,,,
```

### Field Definitions

| Column Name | Clinical Purpose | Code System Example | Description |
|:---|:---|:---|:---|
| `patient_id` | Unique Subject Identifier | Internal MRN | Patient identifier |
| `birth_date` | Date of Birth | ISO-8601 (`YYYY-MM-DD`) | Used for CQL age calculation as of anchor date |
| `gender` | Administrative Sex | `male`, `female`, `other` | Demographics filter (e.g., CMS125 female-only) |
| `encounter_code` | Outpatient Encounter Code | CPT (`99213`, `99214`) | Validates qualifying visit in measurement period |
| `encounter_date` | Date of Encounter | ISO-8601 (`YYYY-MM-DD`) | Visit timestamp |
| `condition_code` | Active Clinical Diagnosis | ICD-10-CM / SNOMED CT | Identifies chronic conditions (`E11.9`, `I10`, `C18.9`) |
| `condition_status`| Clinical Status | `active`, `resolved` | Active state validation |
| `observation_code`| Lab / Biometric Identifier | LOINC | LOINC test code (`4548-4` HbA1c, `8480-6` Systolic BP) |
| `observation_value`| Numeric Observation Result | Float | Quantitative result value (e.g., `7.4`%, `128.0` mmHg) |
| `procedure_code` | Clinical Procedure / Screening | CPT / HCPCS | Screening code (`45378` Colonoscopy, `77067` Mammogram) |
| `procedure_date` | Performance Date | ISO-8601 (`YYYY-MM-DD`) | Procedure timestamp for lookback arithmetic |
| `medication_code` | Prescribed Medication | RxNorm / Generic Name | Medication reconciliation tracking |

---

## 🧪 Testing & Verification

Run the full pytest suite:
```bash
python -m pytest -p no:zarr
```

Run CLI batch smoke test:
```bash
python cli.py batch -i sample.csv -o out_smoke.csv
```

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
