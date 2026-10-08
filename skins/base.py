"""Skin contract plus the drawing bits every skin shares.

A skin is a class of classmethods -- never instantiated -- so switching skins at
runtime is just rebinding a name.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen

from pose import Pose

KEY_BODY = QColor("#CDD3DB")
KEY_FACE = QColor("#F3F5F8")
KEY_EDGE = QColor("#98A2AE")


def pen(color: QColor, width: float = 3.0) -> QPen:
    p = QPen(color, width)
    p.setCapStyle(Qt.RoundCap)
    p.setJoinStyle(Qt.RoundJoin)
    return p


def merged(
    p: QPainter,
    shapes: list[QPainterPath],
    outline: QColor,
    fill: QBrush,
    stroke: float = 3.0,
    capsules: list[tuple[QPointF, QPointF, float]] | None = None,
) -> None:
    """Draw overlapping shapes as one silhouette with a single outer outline.

    Two passes, each in a single colour: first everything in `outline` with a
    doubled pen (so the ink reaches `stroke` past every edge), then everything in
    `fill` with no pen. Because each pass is monochrome the internal boundaries
    are invisible, and what is left is a rim around the merged shape.

    This exists because the obvious alternatives do not work. `QPainterPath.
    simplified()` only fixes winding -- it keeps every sub-shape's boundary, so
    stroking it draws a pile of bubbles. `united()` is correct but costs a
    boolean op per shape per frame. Drawing each piece outlined separately is
    what makes hair read as a wreath of separate leaves and arms read as sausages
    laid on the body.

    Note the sub-shapes must be separate paths, not subpaths of one path:
    overlapping subpaths fill odd-even, and the overlaps punch holes.
    """
    caps = capsules or []

    p.setPen(pen(outline, stroke * 2.0))
    p.setBrush(QBrush(outline))
    for shape in shapes:
        p.drawPath(shape)
    p.setBrush(Qt.NoBrush)
    for a, b, w in caps:
        p.setPen(pen(outline, w + stroke * 2.0))
        p.drawLine(a, b)

    p.setPen(Qt.NoPen)
    p.setBrush(fill)
    for shape in shapes:
        p.drawPath(shape)
    p.setBrush(Qt.NoBrush)
    for a, b, w in caps:
        q = QPen(fill, w)
        q.setCapStyle(Qt.RoundCap)
        q.setJoinStyle(Qt.RoundJoin)
        p.setPen(q)
        p.drawLine(a, b)


class Skin:
    """Subclasses set the metadata and implement `draw`."""

    KEY = "base"
    NAME = "Base"
    ART_W = 200.0
    ART_H = 180.0
    MARGIN = 5.0
    # Head bounding box in art coords (x, y, size) -- used to crop the tray icon.
    ICON_CROP = (50.0, 17.0, 100.0)
    OUTLINE = QColor("#4A3528")

    @classmethod
    def canvas(cls) -> tuple[float, float]:
        return cls.ART_W + cls.MARGIN * 2.0, cls.ART_H + cls.MARGIN * 2.0

    @classmethod
    def render(cls, p: QPainter, pose: Pose) -> None:
        """Entry point for the widget: applies the safety margin, then draws."""
        p.setRenderHint(QPainter.Antialiasing, True)
        p.save()
        p.translate(cls.MARGIN, cls.MARGIN)
        cls.draw(p, pose)
        p.restore()

    @classmethod
    def draw(cls, p: QPainter, pose: Pose) -> None:  # pragma: no cover - abstract
        raise NotImplementedError

    # -- shared props ----------------------------------------------------

    @classmethod
    def draw_keyboard(cls, p: QPainter) -> None:
        base = QRectF(22.0, 134.0, 156.0, 26.0)
        p.setPen(pen(cls.OUTLINE, 3.0))
        p.setBrush(QBrush(KEY_BODY))
        p.drawRoundedRect(base, 6.0, 6.0)

        p.setPen(QPen(KEY_EDGE, 1.4))
        p.setBrush(QBrush(KEY_FACE))
        for y, n, inset in ((139.0, 11, 0.0), (149.0, 10, 6.0)):
            span = 148.0 - inset * 2.0
            w = span / n - 2.0
            for i in range(n):
                x = 26.0 + inset + i * (w + 2.0)
                p.drawRoundedRect(QRectF(x, y, w, 7.5), 1.8, 1.8)

    @classmethod
    def draw_zzz(cls, p: QPainter, phase: float, cx: float, cy: float) -> None:
        # Stroked by hand rather than drawText: no font dependency, so a frozen
        # exe on a machine with odd font fallbacks shows a Z and not a tofu box.
        p.setBrush(Qt.NoBrush)
        for i in range(3):
            t = (phase + i / 3.0) % 1.0
            alpha = int(215 * math.sin(math.pi * t))
            if alpha <= 6:
                continue
            s = 9.0 + t * 9.0
            x = cx + 30.0 + t * 20.0
            y = cy - 34.0 - t * 32.0
            q = QPen(QColor(92, 112, 164, alpha), 1.6 + s * 0.16)
            q.setCapStyle(Qt.RoundCap)
            q.setJoinStyle(Qt.MiterJoin)
            p.setPen(q)
            z = QPainterPath(QPointF(x, y))
            z.lineTo(QPointF(x + s, y))
            z.lineTo(QPointF(x, y + s))
            z.lineTo(QPointF(x + s, y + s))
            p.drawPath(z)
