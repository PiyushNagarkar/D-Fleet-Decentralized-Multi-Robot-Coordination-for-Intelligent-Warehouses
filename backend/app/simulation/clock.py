"""Deterministic simulation clock and timekeeper for D-Fleet."""

from __future__ import annotations
import random
from typing import Optional


class SimulationClock:
    """Deterministic, discrete-event simulation clock.

    Advances simulation time tick-by-tick. Maintains an internal deterministic
    random number generator seeded on construction or reset.
    """

    def __init__(
        self,
        dt: float = 0.1,
        seed: Optional[int] = 42,
    ):
        self.dt: float = dt
        self._initial_seed: Optional[int] = seed
        self._rng: random.Random = random.Random(seed)
        self._current_tick: int = 0
        self._is_paused: bool = False
        self._step_multiplier: float = 1.0

    @property
    def current_tick(self) -> int:
        """Returns the current discrete tick count."""
        return self._current_tick

    @property
    def current_time_s(self) -> float:
        """Returns total elapsed simulated time in seconds."""
        return self._current_tick * self.dt

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    @property
    def rng(self) -> random.Random:
        """RNG seeded deterministically with the clock."""
        return self._rng

    def pause(self) -> None:
        self._is_paused = True

    def resume(self) -> None:
        self._is_paused = False

    def toggle_pause(self) -> bool:
        self._is_paused = not self._is_paused
        return self._is_paused

    def set_speed(self, multiplier: float) -> None:
        if multiplier > 0:
            self._step_multiplier = multiplier

    def tick(self) -> int:
        """Advance time by one discrete tick.

        Returns:
            The new tick number.
        """
        if not self._is_paused:
            self._current_tick += 1
        return self._current_tick

    def reset(self, seed: Optional[int] = None) -> None:
        """Reset the clock back to tick 0 and re-seed RNG."""
        self._current_tick = 0
        self._is_paused = False
        effective_seed = seed if seed is not None else self._initial_seed
        self._rng = random.Random(effective_seed)
