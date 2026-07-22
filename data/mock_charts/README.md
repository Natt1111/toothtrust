# Mock Charts

Synthetic dental chart data and mock X-ray images for development and testing.

**Read-only fixtures.** `DentrixMock` (`src/integrations/dentrix_mock.py`) optionally
loads `*.json` files from this directory at startup to seed example patients, but it
never writes back here — all chart writes stay in an in-memory dict for the life of
the process. See [docs/PRODUCTION_PATH.md](../../docs/PRODUCTION_PATH.md).

## Contents

- `*.png` / `*.jpg` — synthetic periapical and bitewing X-ray images (not real patient data)
- `*.json` — mock Dentrix chart exports, read at startup only

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
