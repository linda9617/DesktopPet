"""Turns coarse input events into a continuously-tweened Pose.

Nothing here is frame-based. A keypress fires a decaying impulse on one paw, so
fast typing produces overlapping taps instead of a fixed animation that has to
finish before the next key is allowed to register.
"""

from __future__ import annotations

import math
import random

from pose import Pose

TAP_DECAY = 0.11        # seconds for a paw to rise and fall back onto the keys
BLINK_TIME = 0.13
SURPRISE_DECAY = 0.30
TWITCH_DECAY = 0.22
YAWN_TIME = 1.30


def _approach(cur: float, target: float, rate: float, dt: float) -> float:
    """Exponential smoothing that is stable at any frame time."""
    return target + (cur - target) * math.exp(-rate * dt)


class PetBrain:
    def __init__(self, idle_yawn_s: float = 40.0, idle_sleep_s: float = 75.0) -> None:
        self.idle_yawn_s = idle_yawn_s
        self.idle_sleep_s = idle_sleep_s
        self.pose = Pose()

        self._t = 0.0
        self._idle = 0.0
        self._since_key = 99.0

        self._tap = {"L": 0.0, "R": 0.0}
        self._space_side = "L"
        self._surprise = 0.0
        self._twitch = {"L": 0.0, "R": 0.0}

        self._blink = 0.0
        self._next_blink = random.uniform(2.0, 5.0)

        self._yawn = -1.0
        self._yawned = False
        self._asleep = False
        self._zzz = 0.0

        self._look = (0.0, 0.0)
        self._last_cursor: tuple[int, int] | None = None

    # ---- events -----------------------------------------------------------

    def on_key(self, side: str) -> None:
        if side == "S":
            side = self._space_side
            self._space_side = "R" if side == "L" else "L"
        self._tap[side] = 1.0
        self._since_key = 0.0
        self._wake()

    def on_click(self, left: bool) -> None:
        self._surprise = 1.0
        self._twitch["L" if left else "R"] = 1.0
        self._wake()

    def _wake(self) -> None:
        self._idle = 0.0
        if self._asleep:
            self._asleep = False
            self._surprise = max(self._surprise, 0.85)
            self._blink = 0.0
        self._yawned = False
        self._yawn = -1.0

    # ---- per-frame --------------------------------------------------------

    def update(self, dt: float, cursor: tuple[int, int], center: tuple[int, int]) -> Pose:
        self._t += dt
        self._since_key += dt

        if self._last_cursor is not None and cursor != self._last_cursor:
            dx = cursor[0] - self._last_cursor[0]
            dy = cursor[1] - self._last_cursor[1]
            if dx * dx + dy * dy > 9:  # ignore sub-pixel jitter
                self._idle = 0.0
                if self._asleep:
                    self._wake()
        self._last_cursor = cursor
        self._idle += dt

        self._decay(dt)
        self._drowsiness(dt)
        self._aim(dt, cursor, center)
        self._blinking(dt)
        return self._compose()

    def _decay(self, dt: float) -> None:
        for side in ("L", "R"):
            self._tap[side] = max(0.0, self._tap[side] - dt / TAP_DECAY)
            self._twitch[side] = max(0.0, self._twitch[side] - dt / TWITCH_DECAY)
        self._surprise = max(0.0, self._surprise - dt / SURPRISE_DECAY)

    def _drowsiness(self, dt: float) -> None:
        if self._asleep:
            self._zzz = (self._zzz + dt * 0.45) % 1.0
            return
        if self._yawn >= 0.0:
            self._yawn += dt / YAWN_TIME
            if self._yawn >= 1.0:
                self._yawn = -1.0
            return
        if self._idle >= self.idle_sleep_s:
            self._asleep = True
            self._zzz = 0.0
        elif self._idle >= self.idle_yawn_s and not self._yawned:
            self._yawned = True
            self._yawn = 0.0

    def _aim(self, dt: float, cursor: tuple[int, int], center: tuple[int, int]) -> None:
        tx = max(-1.0, min(1.0, (cursor[0] - center[0]) / 420.0))
        ty = max(-1.0, min(1.0, (cursor[1] - center[1]) / 300.0))
        if self._asleep:
            tx = ty = 0.0
        lx = _approach(self._look[0], tx, 9.0, dt)
        ly = _approach(self._look[1], ty, 9.0, dt)
        self._look = (lx, ly)

    def _blinking(self, dt: float) -> None:
        if self._asleep:
            return
        if self._blink > 0.0:
            self._blink = max(0.0, self._blink - dt)
            return
        self._next_blink -= dt
        if self._next_blink <= 0.0:
            self._blink = BLINK_TIME
            self._next_blink = random.uniform(2.2, 6.0)

    def _compose(self) -> Pose:
        p = self.pose
        typing = self._since_key < 0.5

        p.paw_l = self._tap["L"]
        p.paw_r = self._tap["R"]

        if self._asleep:
            p.eye_open = 0.0
        elif self._yawn >= 0.0:
            p.eye_open = 0.15 + 0.85 * abs(math.cos(math.pi * self._yawn))
        elif self._blink > 0.0:
            p.eye_open = max(0.0, 1.0 - self._blink / BLINK_TIME * 2.2)
        else:
            p.eye_open = 1.0

        p.look_x, p.look_y = self._look
        p.ear_l = max(self._twitch["L"], self._tap["L"] * 0.35)
        p.ear_r = max(self._twitch["R"], self._tap["R"] * 0.35)
        p.mouth = math.sin(math.pi * self._yawn) if self._yawn >= 0.0 else self._surprise * 0.45
        p.tail = math.sin(self._t * (4.2 if typing else 1.3)) * (1.0 if typing else 0.55)
        p.zzz = self._zzz if self._asleep else -1.0
        p.breath = math.sin(self._t * (1.0 if self._asleep else 2.0))
        p.slump = _approach(p.slump, 1.0 if self._asleep else 0.0, 3.0, 1 / 60.0)
        p.surprise = self._surprise
        return p
