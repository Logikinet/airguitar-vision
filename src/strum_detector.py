"""Right-hand crossing state machine: idle / approach / trigger / cooldown."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from math import hypot
from typing import Optional
from . import config

class StrumState(Enum):
    IDLE = "IDLE"
    APPROACH = "APPROACH"
    TRIGGER = "TRIGGER"
    COOLDOWN = "COOLDOWN"

@dataclass(frozen=True)
class StrumEvent:
    direction: str
    velocity: float
    timestamp_ms: int

def signed_distance(point: tuple[float, float],
                    line: tuple[tuple[float, float], tuple[float, float]]) -> float:
    (ax, ay), (bx, by) = line
    length = hypot(bx - ax, by - ay)
    if length <= 1e-8:
        raise ValueError("Strum line must be nondegenerate")
    return ((bx - ax) * (point[1] - ay) - (by - ay) * (point[0] - ax)) / length

class StrumDetector:
    def __init__(self, v_th: float, cooldown_ms: int, approach_margin: float,
                 approach_timeout_ms: int = config.APPROACH_TIMEOUT_MS) -> None:
        if v_th <= 0 or cooldown_ms < 0 or approach_margin <= 0 or approach_timeout_ms <= 0:
            raise ValueError("Bad strum thresholds")
        self._v_th = v_th
        self._cooldown_ms = cooldown_ms
        self._approach_margin = approach_margin
        self._timeout_ms = approach_timeout_ms
        self._state = StrumState.IDLE
        self._side0: Optional[float] = None
        self._prev_dist: Optional[float] = None
        self._t_approach: Optional[int] = None
        self._t_trigger: Optional[int] = None

    def reset(self) -> None:
        self._state = StrumState.IDLE
        self._side0 = self._prev_dist = self._t_approach = self._t_trigger = None

    @property
    def state(self) -> StrumState:
        return self._state

    def update(self, tip_xy: Optional[tuple[float, float]],
               tip_vel: Optional[tuple[float, float]],
               neck_line: tuple[tuple[float, float], tuple[float, float]],
               now_ms: int) -> Optional[StrumEvent]:
        if tip_xy is None or tip_vel is None:
            self._state = StrumState.IDLE
            self._prev_dist = self._side0 = None
            return None
        (ax, ay), (bx, by) = neck_line
        length = hypot(bx - ax, by - ay)
        if length < 1:
            raise ValueError("Strum segment too short")
        tx, ty = (bx-ax) / length, (by-ay) / length
        tangent = (tip_xy[0] - ax) * tx + (tip_xy[1] - ay) * ty
        if not (-10 <= tangent <= length + 10):
            self._state = StrumState.IDLE
            self._prev_dist = self._side0 = None
            return None
        d = signed_distance(tip_xy, neck_line)
        vn = tx * tip_vel[1] - ty * tip_vel[0]
        if self._state == StrumState.COOLDOWN:
            if self._t_trigger is not None and now_ms - self._t_trigger < self._cooldown_ms:
                self._prev_dist = d
                return None
            self._state = StrumState.IDLE
            self._side0 = None
        if self._state == StrumState.IDLE:
            if (abs(d) <= self._approach_margin and abs(vn) >= self._v_th * .5 and
                    d * vn < 0):
                self._state = StrumState.APPROACH
                self._side0 = d
                self._t_approach = now_ms
            # If a fast frame jumps across the line, use previous distance.
            elif (self._prev_dist is not None and
                  self._prev_dist * d < 0 and abs(vn) >= self._v_th and
                  abs(self._prev_dist) <= self._approach_margin * 1.5):
                self._side0 = self._prev_dist
                self._t_approach = now_ms
                self._state = StrumState.APPROACH
        if self._state == StrumState.APPROACH:
            if self._t_approach is not None and now_ms - self._t_approach > self._timeout_ms:
                self._state = StrumState.IDLE
            elif self._side0 is not None and self._side0 * d <= 0 and abs(vn) >= self._v_th:
                self._state = StrumState.TRIGGER
                event = StrumEvent("down" if vn > 0 else "up", abs(vn), now_ms)
                self._state = StrumState.COOLDOWN
                self._t_trigger = now_ms
                self._prev_dist = d
                return event
            elif abs(d) > self._approach_margin * 1.6:
                self._state = StrumState.IDLE
        self._prev_dist = d
        return None
