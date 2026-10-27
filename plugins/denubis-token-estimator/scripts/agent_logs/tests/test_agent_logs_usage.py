"""Cost units weigh each of a record's four token fields by that field's own weight.

The default weights are the 2026-10-09 probe's uncalibrated proxy: input and cache
creation at 1, cache read at 0.1, output at 5. Expected totals are worked by hand.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from denubis_agent_logs.claude import UsageRecord
from denubis_agent_logs.usage import UNCALIBRATED_WEIGHTS, CostWeights, cost_units


def _record(*, input_tokens, cache_creation, cache_read, output) -> UsageRecord:
    return UsageRecord(
        message_id="msg_1",
        model="claude-opus-4-7",
        session_id="s1",
        cwd="/work",
        timestamp=datetime(2026, 10, 1, tzinfo=UTC),
        input_tokens=input_tokens,
        cache_creation_input_tokens=cache_creation,
        cache_read_input_tokens=cache_read,
        output_tokens=output,
        is_main=True,
        path=Path("/unused.jsonl"),
    )


# Each field holds a different power of ten, so a weight applied to the wrong
# field changes the total.
RECORD = _record(input_tokens=1, cache_creation=10, cache_read=100, output=1000)


def test_default_weights_are_the_uncalibrated_probe_proxy():
    # 1*1 + 1*10 + 0.1*100 + 5*1000
    assert cost_units(RECORD) == pytest.approx(5021.0)
    assert cost_units(RECORD, UNCALIBRATED_WEIGHTS) == pytest.approx(5021.0)


def test_each_weight_applies_to_its_own_token_field():
    weights = CostWeights(input=2, cache_creation=3, cache_read=5, output=7)

    # 2*1 + 3*10 + 5*100 + 7*1000
    assert cost_units(RECORD, weights) == pytest.approx(7532.0)


@pytest.mark.parametrize(
    ("weights", "expected"),
    [
        (CostWeights(input=1, cache_creation=0, cache_read=0, output=0), 1),
        (CostWeights(input=0, cache_creation=1, cache_read=0, output=0), 10),
        (CostWeights(input=0, cache_creation=0, cache_read=1, output=0), 100),
        (CostWeights(input=0, cache_creation=0, cache_read=0, output=1), 1000),
    ],
)
def test_a_lone_weight_selects_exactly_one_field(weights, expected):
    assert cost_units(RECORD, weights) == pytest.approx(expected)
