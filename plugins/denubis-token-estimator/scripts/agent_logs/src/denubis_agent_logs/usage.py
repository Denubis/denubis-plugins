"""Weigh a usage record's token counts into one cost unit.

The weights are a proxy for relative price, not a measured quota mapping. The
default, :data:`UNCALIBRATED_WEIGHTS`, is the 2026-10-09 usage probe's guess at
Anthropic's price ratios, weighted equally across models; replace it once quota
percentages have been regressed on token counts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from denubis_agent_logs.claude import UsageRecord


@dataclass(frozen=True, slots=True)
class CostWeights:
    """One weight per token field of a usage record."""

    input: float
    cache_creation: float
    cache_read: float
    output: float


UNCALIBRATED_WEIGHTS = CostWeights(input=1, cache_creation=1, cache_read=0.1, output=5)


def cost_units(
    record: UsageRecord, weights: CostWeights = UNCALIBRATED_WEIGHTS
) -> float:
    """Return the weighted sum of the record's four token counts."""
    return (
        weights.input * record.input_tokens
        + weights.cache_creation * record.cache_creation_input_tokens
        + weights.cache_read * record.cache_read_input_tokens
        + weights.output * record.output_tokens
    )
