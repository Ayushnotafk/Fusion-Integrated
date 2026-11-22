import json
from pathlib import Path

import pytest


DESIGN = json.loads(
    (Path(__file__).resolve().parents[3] / "gymkhana_test_design.json").read_text(
        encoding="utf-8"
    )
)
CASES = [
    pytest.param(
        scenario,
        marks=pytest.mark.skip(
            reason=(
                "NOT_AUTOMATED: The frozen base does not install or mount "
                "modules.gymkhana, so no executable backend interface is available."
            )
        ),
        id=f"{scenario['test_id']}__{scenario['source_id']}",
    )
    for scenario in DESIGN["test_designs"]["BR"].values()
    for scenario in scenario.get("test_scenarios", [])
]


@pytest.mark.parametrize("scenario", CASES)
def test_supplied_business_rule_not_automated(scenario):
    """The pytest case ID contains the supplied test_id and source_id."""
