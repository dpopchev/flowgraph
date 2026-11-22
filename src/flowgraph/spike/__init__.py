"""A Spike: a question to answer, the kind of work item whose ids are written `Q-0001`."""

from flowgraph.spike.model import (
    SPIKE,
    SpikeIdError,
    make_spike,
    make_spike_id,
    next_spike_id,
    parse_spike_id,
    spike_id_text,
)

__all__ = [
    "SPIKE",
    "SpikeIdError",
    "make_spike",
    "make_spike_id",
    "next_spike_id",
    "parse_spike_id",
    "spike_id_text",
]
