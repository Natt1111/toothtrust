# Mock Cases

Synthetic (non-PHI) patient cases used for development, testing, and demo.

## Format

Each case is a JSON file:

```json
{
  "case_id": "mock_001",
  "patient": {
    "age": 45,
    "sex": "F",
    "medical_history": ["hypertension", "bisphosphonate therapy"],
    "chief_complaint": "sensitivity lower left"
  },
  "proposed_treatment": [
    { "tooth": 19, "procedure": "crown", "cdt": "D2740" },
    { "tooth": 18, "procedure": "extraction", "cdt": "D7210" }
  ],
  "xray_path": "data/mock_charts/mock_001_xray.png",
  "expected_audit_flags": ["bisphosphonate risk — MRONJ", "extraction contraindicated"]
}
```

## Cases

| ID | Scenario | Key audit flags |
|---|---|---|
| (empty — add cases here) | | |
