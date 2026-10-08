"""A cloud-shaped white cat, bongo-cat flavoured.

Flat white, one thick dark outline, bean eyes and an omega mouth -- but the
silhouette is a cloud: lobed all the way round instead of a smooth torso.

Head, body, ears, tail, arms and paws are all one silhouette with a single
continuous outline, which is what stops the arms reading as sausages laid on top
of the torso. That is done without any boolean geometry: `_silhouette` paints
every shape twice, first in solid outline colour with a doubled pen, then in the
fill gradient with no pen. Each pass is one colour, so internal boundaries are
invisible and what survives is a STROKE-wide rim around the merged shape.

(`QPainterPath.simplified()` does not work here -- it only fixes winding and
keeps every circle's boundary, so stroking it draws a pile of bubbles.
`united()` does work but costs a boolean op per lobe per frame.)
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QTransform,
)

from pose import Pose
from skins.base import Skin, merged, pen

LINE = QColor("#33333D")
CLOUD = QColor("#FFFFFF")
CLOUD_LOW = QColor("#E2ECF8")
PAD = QColor("#F6A6B2")
PAD_DEEP = QColor("#E4808F")
EAR_IN = QColor("#F9C9D1")

STROKE = 4.0
ARM_W = 19.0

# Head lobes, relative to the head centre. Centres sit near the hull edge with
# small radii so each one actually protrudes -- a big radius on a near-centre
# lobe just fattens the blob and the cloud reads as an egg.
_HEAD = (
    (0.0, 0.0, 26.0),
    (-13.0, -23.0, 15.0), (2.0, -27.0, 16.0), (17.0, -21.0, 15.0),
    (-25.0, -11.0, 14.0), (26.0, -10.0, 14.0),
    (-29.0, 7.0, 14.0), (29.0, 7.0, 14.0),
    (-19.0, 21.0, 15.0), (19.0, 21.0, 15.0),
    (0.0, 26.0, 16.0),
)
# The torso stops at ~132, a whisker above the keyboard (y=134), and stays inside
# x 48..152. Both limits exist so the arms have somewhere to be: a torso wide
# enough to reach the keys swallows the paws and the cat loses its arms entirely.
_BODY = (
    (100.0, 106.0, 26.0),
    (86.0, 95.0, 15.0), (114.0, 95.0, 15.0),
    (75.0, 107.0, 15.0), (125.0, 107.0, 15.0),
    (61.0, 114.0, 13.0), (139.0, 114.0, 13.0),
)


def _grad(y0: float, y1: float, c0: QColor, c1: QColor) -> QBrush:
    g = QLinearGradient(QPointF(0.0, y0), QPointF(0.0, y1))
    g.setColorAt(0.0, c0)
    g.setColorAt(1.0, c1)
    return QBrush(g)


def _disc(x: float, y: float, r: float) -> QPainterPath:
    path = QPainterPath()
    path.addEllipse(QRectF(x - r, y - r, r * 2.0, r * 2.0))
    return path


class CloudCatSkin(Skin):
    KEY = "cloudcat"
    NAME = "云朵猫"
    OUTLINE = LINE
    ICON_CROP = (50.0, 8.0, 100.0)

    @classmethod
    def draw(cls, p: QPainter, pose: Pose) -> None:
        body_dy = pose.breath * 1.2 + pose.slump * 3.0
        hx = 100.0 + pose.look_x * 8.0
        hy = 70.0 + pose.look_y * 5.0 + body_dy + pose.slump * 9.0 - pose.surprise * 2.0

        shapes, capsules, paws = cls._build(pose, hx, hy, body_dy)

        # Keyboard first, whole cat in front of it. The alternative -- torso
        # behind the keys with only the paws in front -- needs the silhouette
        # redrawn under a clip, and any clip wide enough to clear the paw's own
        # outline rim also catches the torso and repaints it over the keys.
        cls.draw_keyboard(p)
        cls._silhouette(p, shapes, capsules, hy - 56.0)
        cls._ear_lining(p, pose, hx, hy)
        cls._face(p, pose, hx, hy)
        cls._pads(p, pose, paws)
        if pose.zzz >= 0.0:
            cls.draw_zzz(p, pose.zzz, hx + 34.0, hy - 26.0)

    # -- silhouette -------------------------------------------------------

    @classmethod
    def _build(cls, pose: Pose, hx: float, hy: float, body_dy: float):
        shapes = [_disc(hx + x, hy + y, r) for x, y, r in _HEAD]
        shapes += [_disc(x, y + body_dy, r) for x, y, r in _BODY]
        shapes += cls._tail(pose.tail, body_dy)
        for side, flick in ((-1.0, pose.ear_l), (1.0, pose.ear_r)):
            shapes.append(cls._ear(hx, hy, side, flick, inner=False))

        capsules = []
        paws = []
        for side, lift in ((-1.0, pose.paw_l), (1.0, pose.paw_r)):
            # The paw swings outward as it lifts, and the lift is deliberately
            # short: raise it straight up any further and it vanishes back into
            # the torso, which kills the one animation the pet exists for.
            sx, sy = 100.0 + side * 20.0, 104.0 + body_dy
            px = 100.0 + side * (27.0 + lift * 7.0)
            py = 150.0 - lift * 11.0
            capsules.append((QPointF(sx, sy), QPointF(px, py), ARM_W))
            shapes.append(cls._paw(px, py))
            paws.append((px, py))
        return shapes, capsules, paws

    @staticmethod
    def _paw(px: float, py: float) -> QPainterPath:
        path = QPainterPath()
        path.addEllipse(QRectF(px - 13.0, py - 9.5, 26.0, 19.0))
        return path

    @classmethod
    def _silhouette(cls, p: QPainter, shapes, capsules, top: float) -> None:
        fill = _grad(top, 152.0, CLOUD, CLOUD_LOW)
        merged(p, shapes, LINE, fill, STROKE, capsules)

    @classmethod
    def _ear(cls, hx: float, hy: float, side: float, flick: float,
             inner: bool) -> QPainterPath:
        if inner:
            ear = QPainterPath(QPointF(-6.0, 11.0))
            ear.quadTo(QPointF(-3.0, -10.0), QPointF(1.0, -13.0))
            ear.quadTo(QPointF(7.0, -8.0), QPointF(8.0, 11.0))
        else:
            ear = QPainterPath(QPointF(-14.0, 15.0))
            ear.quadTo(QPointF(-9.0, -17.0), QPointF(1.0, -22.0))
            ear.quadTo(QPointF(12.0, -14.0), QPointF(15.0, 15.0))
        ear.closeSubpath()
        t = QTransform()
        t.translate(hx + side * 23.0, hy - 33.0)
        t.rotate(side * (15.0 + flick * 18.0))
        return t.map(ear)

    @classmethod
    def _ear_lining(cls, p: QPainter, pose: Pose, hx: float, hy: float) -> None:
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(EAR_IN))
        for side, flick in ((-1.0, pose.ear_l), (1.0, pose.ear_r)):
            p.drawPath(cls._ear(hx, hy, side, flick, inner=True))

    @classmethod
    def _tail(cls, sway: float, body_dy: float) -> list[QPainterPath]:
        """Separate discs, not one multi-subpath path: overlapping subpaths fill
        odd-even, so the overlaps punch holes and the tail comes out segmented
        like a pinecone."""
        tx, ty = 150.0, 100.0 + body_dy
        return [
            _disc(tx + dx, ty + dy, r)
            for dx, dy, r in (
                (0.0, 0.0, 13.0),
                (8.0, -15.0, 12.0),
                (15.0 + sway * 5.0, -29.0, 12.0),
                (11.0 + sway * 10.0, -42.0, 10.0),
            )
        ]

    # -- face -------------------------------------------------------------

    @classmethod
    def _face(cls, p: QPainter, pose: Pose, hx: float, hy: float) -> None:
        open_amt = max(0.0, min(1.0, pose.eye_open))
        for side in (-1.0, 1.0):
            ex = hx + side * 15.0 + pose.look_x * 3.0
            ey = hy + 4.0 + pose.look_y * 2.0
            if open_amt < 0.25:
                p.setBrush(Qt.NoBrush)
                p.setPen(pen(LINE, 3.4))
                lid = QPainterPath(QPointF(ex - 7.0, ey + 1.0))
                lid.quadTo(QPointF(ex, ey - 6.5), QPointF(ex + 7.0, ey + 1.0))
                p.drawPath(lid)
                continue
            r = 6.4 * (1.0 + pose.surprise * 0.28)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(LINE))
            p.drawEllipse(QRectF(ex - r, ey - r * open_amt, r * 2.0, r * open_amt * 2.0))

        cls._mouth(p, pose, hx, hy + 19.0)

    @classmethod
    def _mouth(cls, p: QPainter, pose: Pose, mx: float, my: float) -> None:
        gape = max(0.0, min(1.0, pose.mouth))
        if gape > 0.12:
            h = 5.0 + gape * 14.0
            w = 6.0 + gape * 5.0
            p.setPen(pen(LINE, 3.0))
            p.setBrush(QBrush(PAD_DEEP))
            p.drawEllipse(QRectF(mx - w, my - h * 0.25, w * 2.0, h))
            return
        p.setPen(pen(LINE, 3.2))
        p.setBrush(Qt.NoBrush)
        omega = QPainterPath(QPointF(mx - 9.5, my - 3.0))
        omega.quadTo(QPointF(mx - 4.5, my + 5.0), QPointF(mx, my - 1.0))
        omega.quadTo(QPointF(mx + 4.5, my + 5.0), QPointF(mx + 9.5, my - 3.0))
        p.drawPath(omega)

    # -- paws -------------------------------------------------------------

    @classmethod
    def _pads(cls, p: QPainter, pose: Pose, paws) -> None:
        p.setPen(Qt.NoPen)
        for (px, py), lift in zip(paws, (pose.paw_l, pose.paw_r)):
            p.setBrush(QBrush(PAD))
            p.drawEllipse(QRectF(px - 4.2, py - 0.5, 8.4, 7.2))
            for dx in (-8.2, 0.0, 8.2):
                p.drawEllipse(QRectF(px + dx - 2.5, py - 6.2, 5.0, 4.6))
