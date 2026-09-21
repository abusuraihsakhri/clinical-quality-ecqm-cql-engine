# Clinical Quality eCQM / CQL Engine

### [Open the Live Application →](https://abusuraihsakhri.github.io/clinical-quality-ecqm-cql-engine/)

A small Python reference implementation for evaluating simplified electronic clinical quality measure population logic. It provides a command-line interface, CSV/JSON input helpers, cohort scoring, rationale output, and a browser interface that runs the same Python package locally with Pyodide.

> [!IMPORTANT]
> This repository is not a full Clinical Quality Language (CQL) parser or execution environment, is not certified for clinical decision support, and has not been validated as an implementation of official CMS, ONC, NCQA, or HL7 measure packages. The measure identifiers below are labels used by this reference implementation.

## Implemented rules

The engine currently includes simplified logic for:

| Measure label | Implemented rule |
| --- | --- |
| `CMS130v11` | Colorectal cancer screening |
| `CMS122v11` | Diabetes HbA1c poor control (>9.0% or missing measurement) |
| `CMS125v11` | Breast cancer screening |
| `CMS165v11` | Blood pressure control |
| `CMS68v12` | Documentation of current medications |

Population evaluation reports initial population, denominator, exclusions/exceptions, numerator status, care-gap status, rationale, and an aggregate performance rate. The default measurement period is `2026-01-01` through `2026-12-31`.

## Browser application

The GitHub Pages application runs the Python engine in the browser through Pyodide. It includes:

- a compact responsive interface for desktop and mobile;
- light and dark themes;
- example inputs for each implemented rule;
- paired observation fields for blood-pressure evaluation;
- population-status and rationale output.

Patient inputs are processed in the browser. The application does not upload patient data to this repository or to an application backend. The Pyodide runtime itself is loaded from the pinned jsDelivr distribution.

Use synthetic or non-identifiable data for demonstrations. This project is not intended for production handling of protected health information.

## Command-line use

Requires Python 3.10 or newer.

```bash
python -m pip install .
clinical-quality-ecqm-cql-engine --list-measures
```

Run the included sample cohort:

```bash
clinical-quality-ecqm-cql-engine --measure CMS130v11
```

Evaluate a CSV file and export patient-level results:

```bash
clinical-quality-ecqm-cql-engine batch \
  --input sample.csv \
  --output results.csv \
  --measure CMS130v11
```

JSON input is supported through the root command:

```bash
clinical-quality-ecqm-cql-engine \
  --file patients.json \
  --measure CMS165v11 \
  --json
```

The repository-level `cli.py` remains as a compatibility wrapper:

```bash
python cli.py --list-measures
```

## Input model

The engine represents patients with demographics plus lists of encounters, conditions, observations, procedures, and medications. The included `sample.csv` shows the flat CSV schema accepted by batch mode.

Dates use ISO `YYYY-MM-DD` format. Supported code sets in this implementation are explicit constants in `ecqm_cql_engine/engine.py`; they are intentionally limited and should not be treated as complete terminology value sets.

## Development and testing

No runtime Python dependencies are required.

```bash
python -m pip install . pytest
python -m compileall -q ecqm_cql_engine cli.py tests
python -m pytest -p no:zarr -v
python cli.py batch -i sample.csv -o out_smoke.csv
```

Continuous integration tests Python 3.10 through 3.14, verifies package installation and the installed console entry point, compiles the Python sources, runs the test suite, and performs CLI and static web smoke checks.

## Technology

- Python standard library
- Pyodide for in-browser Python execution
- HTML, CSS, and JavaScript
- GitHub Actions
- GitHub Pages

The web application requires a modern browser with WebAssembly support and network access to load the pinned Pyodide runtime.

## License

MIT License. See [LICENSE](LICENSE).
