import json
from pathlib import Path

import pytest


DESIGN = json.loads(
    (Path(__file__).resolve().parents[3] / "gymkhana_test_design.json").read_text(
        encoding="utf-8"
    )
)
def _scenarios(value):
    if isinstance(value, dict):
        if "test_id" in value:
            yield value
        else:
            for child in value.values():
                yield from _scenarios(child)
    elif isinstance(value, list):
        for child in value:
            yield from _scenarios(child)


CASES = [
    pytest.param(
        scenario,
        marks=pytest.mark.skip(
            reason="NOT_AUTOMATED: No backend interface exists for this supplied scenario."
        ),
        id=f"{scenario['test_id']}__{scenario['source_id']}",
    )
    for scenario in _scenarios(DESIGN["test_designs"]["FR"])
]


@pytest.mark.parametrize("scenario", CASES)
def test_supplied_functional_scenario_not_automated(scenario):
    """The pytest case ID contains the supplied test_id and source_id."""
