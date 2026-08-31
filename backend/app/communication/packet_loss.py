"""Packet Loss Models for Peer-to-Peer Communication Simulation."""

from __future__ import annotations
import random
from typing import Optional


class PacketLossModel:
    """Simulates packet drop behaviors on simulated network links."""

    def __init__(
        self,
        loss_rate: float = 0.0,
        burst_loss_rate: float = 0.0,
        seed: Optional[int] = 42,
    ):
        self.loss_rate = max(0.0, min(1.0, loss_rate))
        self.burst_loss_rate = max(0.0, min(1.0, burst_loss_rate))
        self._rng = random.Random(seed)
        self._in_burst: bool = False

    def is_packet_dropped(self) -> bool:
        """Evaluate if the next packet should be dropped."""
        if self.loss_rate >= 1.0:
            return True
        if self.loss_rate <= 0.0:
            return False

        return self._rng.random() < self.loss_rate

    def set_loss_rate(self, rate: float) -> None:
        self.loss_rate = max(0.0, min(1.0, rate))
