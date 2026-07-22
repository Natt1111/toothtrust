"""Tests for DentrixMock — specifically the zero-disk-persistence guarantee.

A real PMS integration must never store patient data locally: fetch on
demand, hold it in memory for the session, write back to the PMS, persist
nothing. These tests prove that contract holds for the mock today, so it
can't silently regress before it's swapped for a real adapter.
"""

from __future__ import annotations

import json

from src.integrations.dentrix_mock import DentrixMock


def test_unknown_patient_returns_empty_scaffold():
    dm = DentrixMock(seed_dir=None)
    chart = dm.get_chart("nobody")
    assert chart == {"patient_id": "nobody", "teeth": {}, "notes": [], "procedures": []}


def test_write_chart_entry_updates_in_memory_state():
    dm = DentrixMock(seed_dir=None)
    dm.write_chart_entry("p001", {"entry_type": "note", "description": "Sensitivity on #19"})
    chart = dm.get_chart("p001")
    assert len(chart["notes"]) == 1
    assert chart["notes"][0]["description"] == "Sensitivity on #19"
    assert "timestamp" in chart["notes"][0]


def test_write_finding_entry_nests_under_tooth():
    dm = DentrixMock(seed_dir=None)
    dm.write_chart_entry("p001", {"entry_type": "finding", "tooth": 19, "description": "Recurrent decay"})
    chart = dm.get_chart("p001")
    assert chart["teeth"]["19"]["findings"] == ["Recurrent decay"]


def test_list_patients_reflects_writes():
    dm = DentrixMock(seed_dir=None)
    assert dm.list_patients() == []
    dm.write_chart_entry("p001", {"entry_type": "note", "description": "x"})
    dm.write_chart_entry("p002", {"entry_type": "note", "description": "y"})
    assert sorted(dm.list_patients()) == ["p001", "p002"]


def test_writes_never_touch_disk(tmp_path):
    """The core guarantee: no chart write, ever, creates or modifies a file."""
    empty_seed_dir = tmp_path / "seed"
    empty_seed_dir.mkdir()

    dm = DentrixMock(seed_dir=empty_seed_dir)
    for i in range(5):
        dm.write_chart_entry(f"patient_{i}", {"entry_type": "procedure", "description": f"proc {i}"})

    assert list(empty_seed_dir.iterdir()) == [], "DentrixMock must never write chart data to disk"


def test_seed_fixtures_are_read_only(tmp_path):
    """Seeding from static fixtures is allowed; writing back to those fixtures is not."""
    seed_dir = tmp_path / "seed"
    seed_dir.mkdir()
    fixture_path = seed_dir / "mock_p001.json"
    original_content = json.dumps({"patient_id": "mock_p001", "teeth": {}, "notes": [], "procedures": []})
    fixture_path.write_text(original_content)

    dm = DentrixMock(seed_dir=seed_dir)
    assert dm.list_patients() == ["mock_p001"]

    dm.write_chart_entry("mock_p001", {"entry_type": "note", "description": "new note"})

    # The write landed in memory...
    assert len(dm.get_chart("mock_p001")["notes"]) == 1
    # ...but the on-disk fixture is untouched.
    assert fixture_path.read_text() == original_content


def test_two_instances_do_not_share_state(tmp_path):
    """No shared backing store between instances — confirms there's no hidden disk/global state."""
    empty_seed_dir = tmp_path / "seed"
    empty_seed_dir.mkdir()

    dm1 = DentrixMock(seed_dir=empty_seed_dir)
    dm1.write_chart_entry("p001", {"entry_type": "note", "description": "only in dm1"})

    dm2 = DentrixMock(seed_dir=empty_seed_dir)
    assert dm2.list_patients() == []
