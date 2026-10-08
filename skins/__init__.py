"""Skin registry.

To add a skin: drop a module in here with a `Skin` subclass and append it to
SKINS. Nothing else in the app needs to change.
"""

from __future__ import annotations

from skins.base import Skin
from skins.cat import CatSkin
from skins.cloudcat import CloudCatSkin
from skins.furina import FurinaSkin
from skins.march7 import March7Skin

SKINS: tuple[type[Skin], ...] = (
    CatSkin,
    CloudCatSkin,
    FurinaSkin,
    March7Skin,
)
DEFAULT = CatSkin

# Keys that have been renamed or removed. Without this a settings.json written by an
# older build quietly falls back to the cat, which looks like the app forgot which skin
# you picked. Every one of these was a variant that either lost to the version that
# replaced it or became the only one left, so they all land on what survived rather
# than on the cat: `furina_photo` was the illustration-crop skin, `furina_short` the
# short-front-locks Furina that is now just `furina`, and `march7_long` the long-haired
# March 7th that is now just `march7`.
ALIASES = {
    "furina_derp": "furina",
    "furina_derp2": "furina",
    "furina_cute": "furina",
    "furina_photo": "furina",
    "furina_short": "furina",
    "march7_long": "march7",
}


def get(key: str | None) -> type[Skin]:
    key = ALIASES.get(key, key)
    for skin in SKINS:
        if skin.KEY == key:
            return skin
    return DEFAULT


__all__ = ["SKINS", "DEFAULT", "Skin", "get"]
