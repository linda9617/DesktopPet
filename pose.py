"""The animation parameter set, shared by every skin.

Field names are the cat's, because it came first, but each skin is free to
reinterpret them -- `ear_l/ear_r` is "something on the head flicks", `tail` is
"something long sways". Keeping one vocabulary means pet.py never has to know
which skin is loaded.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Pose:
    paw_l: float = 0.0       # 0 = resting on the keys, 1 = lifted to strike
    paw_r: float = 0.0
    eye_open: float = 1.0    # 0 = shut, 1 = wide
    look_x: float = 0.0      # -1..1, pupil + head follow the real cursor
    look_y: float = 0.0
    ear_l: float = 0.0       # 0..1 flick (cat ear / hair curl)
    ear_r: float = 0.0
    mouth: float = 0.0       # 0 = closed, 1 = yawning
    tail: float = 0.0        # -1..1 sway (cat tail / hair lock)
    zzz: float = -1.0        # <0 hidden, else 0..1 rising phase
    breath: float = 0.0      # -1..1
    slump: float = 0.0       # 0 = alert, 1 = head down asleep
    surprise: float = 0.0    # 0..1 click reaction
