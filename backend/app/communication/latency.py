"""Network Latency Models for Peer-to-Peer Link Simulation."""

from __future__ import annotations
import random
from typing import Optional


class LatencyModel:
    """Calculates transmission delay for network packets."""

    def __init__(
        self,
        base_latency_ticks: int = 0,
        jitter_ticks: int = 0,
        seed: Optional[int] = 42,
    ):
        self.base_latency_ticks = max(0, base_latency_ticks)
        self.jitter_ticks = max(0, jitter_ticks)
        self._rng = random.Random(seed)

    def calculate_delay(self) -> int:
        """Compute delay in simulation ticks."""
        if self.jitter_ticks == 0:
            return self.base_latency_ticks
        
        jitter = self._rng.randint(-self.jitter_ticks, self.jitter_ticks)
        return max(0, self.base_latency_ticks + jitter)

    def set_latency(self, base_ticks: int, jitter_ticks: int = 0) -> None:
        self.base_latency_ticks = max(0, base_ticks)
        self.jitter_ticks = max(0, jitter_ticks)
