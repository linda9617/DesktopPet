"""Orange tabby skin -- the original."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen

from pose import Pose
from skins.base import Skin, pen

INK = QColor("#4A3528")
FUR = QColor("#F0A05A")
FUR_DARK = QColor("#D9873C")
CREAM = QColor("#FDF3E7")
EAR_IN = QColor("#F2A2A2")
NOSE = QColor("#E4736F")


class CatSkin(Skin):
    KEY = "cat"
    NAME = "橘猫"
    OUTLINE = INK
    ICON_CROP = (50.0, 17.0, 100.0)

    @classmethod
    def draw(cls, p: QPainter, pose: Pose) -> None:
        body_dy = pose.breath * 1.2 + pose.slump * 3.0
        head_cx = 100.0 + pose.look_x * 7.0
        head_cy = 62.0 + pose.look_y * 4.0 + body_dy + pose.slump * 10.0 - pose.surprise * 3.0

        _tail(p, pose, body_dy)
        _body(p, body_dy)
        _head(p, pose, head_cx, head_cy)
        cls.draw_keyboard(p)
        _arms(p, pose, body_dy)
        if pose.zzz >= 0.0:
            cls.draw_zzz(p, pose.zzz, head_cx, head_cy)


def _tail(p: QPainter, pose: Pose, body_dy: float) -> None:
    path = QPainterPath(QPointF(146.0, 132.0 + body_dy))
    path.cubicTo(
        QPointF(176.0, 132.0 + body_dy),
        QPointF(188.0, 108.0 + pose.tail * 14.0),
        QPointF(170.0, 92.0 + pose.tail * 20.0),
    )
    p.setPen(pen(INK, 11.0))
    p.setBrush(Qt.NoBrush)
    p.drawPath(path)
    p.setPen(pen(FUR, 7.0))
    p.drawPath(path)


def _body(p: QPainter, body_dy: float) -> None:
    p.setPen(pen(INK, 3.0))
    p.setBrush(QBrush(FUR))
    p.drawEllipse(QRectF(48.0, 84.0 + body_dy, 104.0, 92.0))
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(CREAM))
    p.drawEllipse(QRectF(70.0, 108.0 + body_dy, 60.0, 68.0))


def _head(p: QPainter, pose: Pose, cx: float, cy: float) -> None:
    _ear(p, cx - 30.0, cy - 26.0, -1.0, pose.ear_l)
    _ear(p, cx + 30.0, cy - 26.0, 1.0, pose.ear_r)

    p.setPen(pen(INK, 3.0))
    p.setBrush(QBrush(FUR))
    p.drawEllipse(QRectF(cx - 45.0, cy - 40.0, 90.0, 80.0))

    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(CREAM))
    p.drawEllipse(QRectF(cx - 26.0, cy + 2.0, 52.0, 30.0))

    _stripes(p, cx, cy)
    _eyes(p, pose, cx, cy)
    _nose_mouth(p, pose, cx, cy)
    _whiskers(p, cx, cy)


def _ear(p: QPainter, x: float, y: float, side: float, twitch: float) -> None:
    lean = side * twitch * 7.0
    outer = QPainterPath(QPointF(x - 16.0 * side, y + 14.0))
    outer.lineTo(QPointF(x + 2.0 * side + lean, y - 20.0 - twitch * 4.0))
    outer.lineTo(QPointF(x + 17.0 * side, y + 8.0))
    outer.closeSubpath()
    p.setPen(pen(INK, 3.0))
    p.setBrush(QBrush(FUR))
    p.drawPath(outer)

    inner = QPainterPath(QPointF(x - 9.0 * side, y + 10.0))
    inner.lineTo(QPointF(x + 1.0 * side + lean * 0.8, y - 12.0 - twitch * 3.0))
    inner.lineTo(QPointF(x + 10.0 * side, y + 6.0))
    inner.closeSubpath()
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(EAR_IN))
    p.drawPath(inner)


def _stripes(p: QPainter, cx: float, cy: float) -> None:
    p.setPen(pen(FUR_DARK, 4.0))
    p.setBrush(Qt.NoBrush)
    for dx, length in ((-12.0, 9.0), (0.0, 12.0), (12.0, 9.0)):
        p.drawLine(QPointF(cx + dx, cy - 34.0), QPointF(cx + dx, cy - 34.0 + length))


def _eyes(p: QPainter, pose: Pose, cx: float, cy: float) -> None:
    open_amt = max(0.0, min(1.0, pose.eye_open))
    for side in (-1.0, 1.0):
        ex, ey = cx + side * 17.0, cy - 2.0

        if open_amt < 0.25:
            p.setPen(pen(INK, 3.0))
            p.setBrush(Qt.NoBrush)
            lid = QPainterPath(QPointF(ex - 9.0, ey))
            lid.quadTo(QPointF(ex, ey + 5.0), QPointF(ex + 9.0, ey))
            p.drawPath(lid)
            continue

        ry = 10.5 * open_amt * (1.0 + pose.surprise * 0.25)
        rx = 8.5 * (1.0 + pose.surprise * 0.2)
        white = QRectF(ex - rx, ey - ry, rx * 2.0, ry * 2.0)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor("#FFFFFF")))
        p.drawEllipse(white)

        # Clip to the sclera so the pupil can ride the rim -- that overshoot is
        # what makes a glance read as a glance rather than a 3px nudge.
        clip = QPainterPath()
        clip.addEllipse(white)
        p.save()
        p.setClipPath(clip)
        pr = min(5.6, ry * 0.72)
        px = ex + pose.look_x * rx * 0.66
        py = ey + pose.look_y * ry * 0.58
        p.setBrush(QBrush(INK))
        p.drawEllipse(QRectF(px - pr, py - pr, pr * 2.0, pr * 2.0))
        p.setBrush(QBrush(QColor(255, 255, 255, 225)))
        p.drawEllipse(QRectF(px - pr * 0.85, py - pr * 0.95, pr * 0.66, pr * 0.66))
        p.restore()

        p.setPen(pen(INK, 2.4))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(white)


def _nose_mouth(p: QPainter, pose: Pose, cx: float, cy: float) -> None:
    nose = QPainterPath(QPointF(cx - 5.0, cy + 10.0))
    nose.lineTo(QPointF(cx + 5.0, cy + 10.0))
    nose.lineTo(QPointF(cx, cy + 15.0))
    nose.closeSubpath()
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(NOSE))
    p.drawPath(nose)

    gape = max(0.0, min(1.0, pose.mouth))
    p.setPen(pen(INK, 2.6))
    if gape > 0.08:
        h = 4.0 + gape * 15.0
        w = 7.0 + gape * 6.0
        p.setBrush(QBrush(QColor("#D2635F")))
        p.drawEllipse(QRectF(cx - w, cy + 15.0, w * 2.0, h))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor("#F09C9C")))
        p.drawEllipse(QRectF(cx - w * 0.45, cy + 15.0 + h * 0.45, w * 0.9, h * 0.42))
        return

    p.setBrush(Qt.NoBrush)
    for side in (-1.0, 1.0):
        lip = QPainterPath(QPointF(cx, cy + 15.0))
        lip.quadTo(QPointF(cx + side * 5.0, cy + 21.0), QPointF(cx + side * 10.0, cy + 16.0))
        p.drawPath(lip)


def _whiskers(p: QPainter, cx: float, cy: float) -> None:
    q = QPen(QColor(74, 53, 40, 150), 1.8)
    q.setCapStyle(Qt.RoundCap)
    p.setPen(q)
    p.setBrush(Qt.NoBrush)
    for side in (-1.0, 1.0):
        for i, dy in enumerate((-2.0, 3.0, 8.0)):
            x0 = cx + side * 24.0
            y0 = cy + 10.0 + dy * 0.6
            path = QPainterPath(QPointF(x0, y0))
            path.quadTo(
                QPointF(x0 + side * 14.0, y0 + dy * 0.3 - 2.0),
                QPointF(x0 + side * 26.0, y0 + dy - 4.0 + i * 1.5),
            )
            p.drawPath(path)


def _arms(p: QPainter, pose: Pose, body_dy: float) -> None:
    for side, lift in ((-1.0, pose.paw_l), (1.0, pose.paw_r)):
        sx, sy = 100.0 + side * 30.0, 116.0 + body_dy
        px = 100.0 + side * (34.0 - lift * 2.5)
        py = 133.0 - lift * 12.0

        p.setPen(pen(INK, 17.0))
        p.drawLine(QPointF(sx, sy), QPointF(px, py))
        p.setPen(pen(FUR, 13.0))
        p.drawLine(QPointF(sx, sy), QPointF(px, py))

        p.setPen(pen(INK, 2.8))
        p.setBrush(QBrush(CREAM))
        p.drawEllipse(QRectF(px - 12.0, py - 8.0, 24.0, 16.0))

        p.setPen(QPen(QColor(74, 53, 40, 120), 1.6))
        p.setBrush(Qt.NoBrush)
        for dx in (-4.0, 0.0, 4.0):
            p.drawLine(QPointF(px + dx, py - 6.0), QPointF(px + dx, py - 1.0))
