# Mock Charts

Synthetic dental chart data and mock X-ray images for development and testing.

## Contents

- `*.png` / `*.jpg` — synthetic periapical and bitewing X-ray images (not real patient data)
- `*.json` — mock Dentrix chart exports

## Generating mock X-rays

For early development, use publicly available dental X-ray datasets with appropriate licensing (e.g., Tufts Dental Database). Store only de-identified images here.

## Mock chart format

```json
{
  "patient_id": "mock_p001",
  "provider": "Dr. Smith",
  "date": "2026-05-17",
  "teeth": {
    "19": { "restorations": ["MOD amalgam"], "conditions": ["recurrent decay"] },
    "18": { "conditions": ["impacted", "pericoronitis"] }
  },
  "periodontal": {
    "pocket_depths": { "19": [3, 4, 3, 3, 4, 4] }
  }
}
```
