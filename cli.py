#!/usr/bin/env python3
"""Compatibility wrapper for the installed package CLI."""

import sys

from ecqm_cql_engine.cli import (
    format_measure_report,
    get_sample_cohort,
    interactive_mode,
    load_patients_from_csv,
    main,
    run_batch_evaluation,
)

__all__ = [
    "format_measure_report",
    "get_sample_cohort",
    "interactive_mode",
    "load_patients_from_csv",
    "main",
    "run_batch_evaluation",
]


if __name__ == "__main__":
    sys.exit(main() or 0)
