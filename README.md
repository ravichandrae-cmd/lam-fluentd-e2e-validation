# Legacy Agent Migration (LAM) Fluentd E2E Validation

A framework for validating exact log parity between `google-fluentd` and the new `oss-fluentd-plugin` when migrating legacy agents.

## Directory Structure

- `scenarios/`: YAML templates defining specific log ingestion scenarios and what fields to validate.
- `scripts/`: Python tools for validating, comparing, reporting, and extracting log outputs.
- `outputs/`: Ignored directory where generated json mock data, raw logs, and validation reports are saved.

## Quick Start

### 1. Configure and Run a Comparison

To compare a set of exported logs against a scenario schema:

```bash
python scripts/compare_logs.py \
  --scenario scenarios/golang_slog_json.yaml \
  --baseline outputs/baseline/golang.json \
  --upstream outputs/upstream/golang.json
```

This script will validate:
- Timestamp presence and InsertId uniqueness.
- Resource Types and Log Names.
- JSON vs Text payload validation.
- Missing or extra logs between agents.
- Deep field-level parity on the defined `comparison_keys`.

It saves a JSON validation result under `outputs/reports/`.

### 2. Generate a Markdown Summary

Once you have generated one or more JSON reports, you can compile them into an easy-to-read markdown file.

```bash
python scripts/report.py
```
This produces a `outputs/reports/summary.md` detailing the pass/fail status and matched discrepancies of all test runs.

### 3. Export Logs (WIP)

You can use the placeholder exporter to pull logs from GCP, ensuring you do not hardcode your Project IDs or credentials.

```bash
python scripts/export_logs.py \
  --project my-gcp-project-id \
  --log-name ravi-golang-app \
  --output outputs/baseline/golang.json
```

## Adding New Scenarios

To add a new scenario, create a `.yaml` file under `scenarios/`. Use the existing templates as a schema reference. Ensure you don't hardcode any secrets inside the YAML! Keep metadata flexible.
