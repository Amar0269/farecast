# Data Collector & Cleaning Subsystem (Member 1 - SIH26056)

This directory contains the core implementation of Member 1's Data Collection and Data Cleaning module.

## Setup & Running

```bash
# Activate virtual environment
source .venv/bin/activate

# Run full test suite (57 tests)
pytest tests/

# Single query collection
python -m pipelines.collect --source yatra --origin DEL --destination BOM --travel-date 2026-10-17

# Bulk sampling matrix collection (6 routes x 5 lead times)
python -m pipelines.collect --run-matrix --source yatra
```

For full details, architecture, and team integration guide, see the root [`README.md`](../README.md).
