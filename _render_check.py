"""Dev helper: render key poses for every skin so the art can be eyeballed.

Usage: python _render_check.py [skin_key ...]   ->  _poses_<key>.png
"""

from __future__ import annotations

import sys

from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPixmap

import skins
from pose import Pose

POSES = [
    ("idle", Pose()),
    ("look left+up", Pose(look_x=-1.0, look_y=-0.8)),
    ("look right+down", Pose(look_x=1.0, look_y=0.9)),
    ("blink", Pose(eye_open=0.0)),
    ("type L", Pose(paw_l=1.0, ear_l=0.35, tail=0.9)),
    ("type R", Pose(paw_r=1.0, ear_r=0.35, tail=-0.9)),
    ("click surprise", Pose(surprise=1.0, mouth=0.45, ear_l=1.0)),
    ("yawn", Pose(mouth=1.0, eye_open=0.15)),
    ("asleep", Pose(eye_open=0.0, slump=1.0, zzz=0.35, breath=-1.0)),
]


def sheet(skin, scale: float = 1.6) -> str:
    cols = 3
    cw_art, ch_art = skin.canvas()
    cw, ch = int(cw_art * scale), int(ch_art * scale) + 22
    rows = (len(POSES) + cols - 1) // cols

    pm = QPixmap(cw * cols, ch * rows)
    pm.fill(QColor("#EFF2F6"))
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    font = QFont()
    font.setPointSize(9)

    for i, (label, pose) in enumerate(POSES):
        ox, oy = (i % cols) * cw, (i // cols) * ch
        p.save()
        p.translate(ox, oy + 20)
        p.scale(scale, scale)
        skin.render(p, pose)
        p.restore()
        p.setFont(font)
        p.setPen(QColor("#33404F"))
        p.drawText(QPointF(ox + 8, oy + 14), label)
        p.setPen(QColor("#C6CED8"))
        p.drawLine(ox, oy, ox, oy + ch)
        p.drawLine(ox, oy, ox + cw, oy)
    p.end()

    out = f"_poses_{skin.KEY}.png"
    pm.save(out)
    print(f"wrote {out}  {pm.width()}x{pm.height()}")
    return out


def main() -> int:
    app = QGuiApplication(sys.argv)
    wanted = sys.argv[1:]
    for skin in skins.SKINS:
        if not wanted or skin.KEY in wanted:
            sheet(skin)
    del app
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
