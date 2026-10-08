"""Blue-and-white hydro-themed chibi skin.

Procedural, code-drawn character inspired by Furina -- white-blue wavy hair,
navy tailcoat, gold-crowned top hat. No official art assets are used or
reproduced; this is fan-style geometry for personal desktop use.

`FurinaBase` owns the hair, hat, coat and arms. `FurinaSkin` adds the face:
plain black bean eyes and a tiny mouth, which is what makes it read as dopey.
The split is a leftover: two other subclasses have lived here and both are gone --
one swapped the drawn head for a crop of a reference illustration, the other only
swapped the front-lock table (its numbers won, and are now the ones below). The
base/subclass seam costs nothing and buys nothing; worth collapsing if this file is
ever touched heavily again. The geometry tables are the part that made the variants
cheap, and they stay.

All the hair in one pass goes through `skins.base.merged`, so a dozen locks come
out as one voluminous mass under a single outline. Outlining each lock separately
turns the hairstyle into a laurel wreath of separate leaves.

Pose reinterpretation: `ear_l` flicks the ahoge, `ear_r` tips the hat, `tail`
sways the long hair.
"""

from __future__ import annotations

import math

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

INK = QColor("#2C3A54")
SKIN = QColor("#FDEADF")
HAIR_W = QColor("#FFFFFF")
HAIR_L = QColor("#F1F7FD")
HAIR_B = QColor("#BCDBF3")
HAIR_B2 = QColor("#86BFE8")
NAVY = QColor("#213E70")
NAVY_L = QColor("#31548F")
NAVY_D = QColor("#152A4F")
GOLD = QColor("#D9A94C")
GOLD_L = QColor("#F2D486")
WHITE = QColor("#FDFDFF")
# Gloves, not bare hands. Sampled off skins/ref/1.webp: her hands there come back
# #FEF3EE / #FBF4E4 / #F9F6EE, while her cheek is #FDE6D7 -- lighter than the face
# and with the pink taken out of it, which is cloth rather than skin. The shadow is
# deliberately cool: warming it turns the glove back into a hand.
GLOVE = QColor("#FCF6EF")
GLOVE_D = QColor("#D3DBE8")
GEM = QColor("#4E9FE0")
BLUSH_C = QColor("#F5A0AC")
LIP = QColor("#D9737F")
EYE_L = QColor("#A8DCF8")
EYE_D = QColor("#2F5FA8")

STROKE = 3.0

# Hair lobes relative to the head centre. Deliberately reaching well past the
# head (which is only ~39 wide) -- the volume is the character.
#
# The lowest lobe stops at +66: the hair is drawn behind the keyboard (y 134..160)
# so its ends are meant to vanish under it, but the head also drops ~11px when she
# slumps asleep, and anything reaching past +80 pokes out below the keys.
# Radii are deliberately uneven. Equal lobes all round give a regular scallop
# that reads as a poodle; mixing 15..24 breaks it into waves.
_BACK_HAIR = (
    (0.0, -4.0, 43.0),
    (-27.0, -29.0, 21.0), (1.0, -41.0, 24.0), (28.0, -27.0, 19.0),
    (-46.0, -2.0, 23.0), (45.0, 1.0, 20.0),
    (-50.0, 22.0, 18.0), (49.0, 21.0, 21.0),
    (-44.0, 44.0, 18.0), (47.0, 46.0, 16.0),
)

# The pair of locks that frames the face, as `(dx, dy, w, h, rot, sway_dy, sway_rot)`
# relative to the head centre. A table rather than literals in the method: this is the
# second set of numbers to live here and it will not be the last.
#
# The first set ran the lower pair out to y=135 with the arms drawn *after* them, so the
# tips ended under the sleeve. That looked like hair stopping at the shoulder, because a
# hidden tip is not length -- it is a tip you cannot see. These numbers pull the lower
# pair in over the shoulder and cut it to h=18, tips at y=118, and the arms are drawn
# first so the hair lies in front of them. Shorter in numbers, longer on screen.
#
# y=118 is set by the *cuff*, not by the hand. The gold cuff sits 11 units back from the
# glove, and a keypress swings the arm up until the cuff spans y 119..134 -- so the naive
# clearance (glove top y=125.5) is 7 units too generous. Add the outline, which juts the
# full 3 units past the path (`merged` strokes at STROKE*2), and a tip at 118 reads down
# to 121 and still never touches metal. A lock crossing the cuff amputates the arm and
# the glove becomes a ball floating beside her; one crossing the upper arm just below the
# shoulder reads as hair lying over a sleeve, which is the whole point.
#
# dx is 34, not 39, so each lower lock continues its upper lock's axis instead of sitting
# outboard of it (that leaves a step in the silhouette where the two overlap). The tips
# land mid-sleeve -- x 68 / 132 against a sleeve spanning x 59..77 / 123..141 at that
# height. Nudged outward instead they finish on the sleeve's outer edge, and a tip sitting
# exactly on a silhouette line reads as a notch cut in the arm.
_FRONT_LOCKS = (
    (-36.0, 6.0, 24.0, 40.0, -6.0, 0.0, 0.0),
    (-34.0, 30.0, 20.0, 18.0, -6.0, 1.0, 4.0),
    (37.0, 4.0, 24.0, 42.0, 6.0, 0.0, 0.0),
    (34.0, 30.0, 20.0, 18.0, 7.0, -1.0, -4.0),
)


def _hair_fill(top: float) -> QBrush:
    """White down to two-thirds, blue only in the tips -- the reference hair is a
    white head of hair with blue ends, not blue hair."""
    g = QLinearGradient(QPointF(0.0, top), QPointF(0.0, 152.0))
    g.setColorAt(0.0, HAIR_W)
    g.setColorAt(0.52, HAIR_L)
    g.setColorAt(0.80, HAIR_B)
    g.setColorAt(1.0, HAIR_B2)
    return QBrush(g)


def _grad(x0: float, y0: float, x1: float, y1: float, c0: QColor, c1: QColor) -> QBrush:
    g = QLinearGradient(QPointF(x0, y0), QPointF(x1, y1))
    g.setColorAt(0.0, c0)
    g.setColorAt(1.0, c1)
    return QBrush(g)


def _disc(x: float, y: float, r: float) -> QPainterPath:
    path = QPainterPath()
    path.addEllipse(QRectF(x - r, y - r, r * 2.0, r * 2.0))
    return path


def _lock(x: float, y: float, w: float, h: float, rot: float) -> QPainterPath:
    """A tapering lock: round at the root, pointed at the tip.

    Stroking a curve with a fat pen instead gives a constant-width rope, which
    reads as cable rather than hair.
    """
    path = QPainterPath(QPointF(0.0, h))
    path.cubicTo(QPointF(-w * 0.58, h * 0.42), QPointF(-w * 0.58, -h * 0.38),
                 QPointF(0.0, -h * 0.5))
    path.cubicTo(QPointF(w * 0.58, -h * 0.38), QPointF(w * 0.58, h * 0.42),
                 QPointF(0.0, h))
    path.closeSubpath()
    t = QTransform()
    t.translate(x, y)
    t.rotate(rot)
    return t.map(path)


class FurinaBase(Skin):
    OUTLINE = INK
    HEAD_CY = 66.0
    HEAD_RX = 38.0
    HEAD_RY = 39.0
    ICON_CROP = (42.0, 2.0, 116.0)
    HAT_ROT = 14.0
    HAT_FEATHER = False
    # Hat size, split by axis, and where it is pinned relative to the head centre.
    #
    # Split because there is almost no room above the head -- the hair already tops out
    # near y=1 on a 180-unit canvas (art coords survive to -5, the MARGIN) -- so a hat
    # that wants to look bigger has to buy most of it in *width*, where there is room,
    # and only a little in height. The two failed alternatives: scaling both axes runs
    # the crown off the top edge, and pinning the hat lower to compensate buries the
    # brim in the hair, at which point the crown is a navy slab and the whole thing
    # stops reading as a top hat. Brim and crown together are what make the shape --
    # lose either and it is just a box.
    HAT_SCALE_X = 1.0
    HAT_SCALE_Y = 1.0
    HAT_ANCHOR = (21.0, -26.0)
    # Ahoge, same treatment and same reason: rooted at the top of the skull, so length
    # comes from leaning it over rather than from standing it up taller. Width is kept
    # near 1 on purpose -- a proportionally fattened strand stops looking like hair and
    # starts looking like a feather or a horn.
    AHOGE_SCALE_X = 1.0
    AHOGE_SCALE_Y = 1.0
    AHOGE_LEAN = 0.0
    # Coat shoulder half-width; the hem is narrower (see _coat). A straight taper
    # from a point at the neck out to a wide hem has no shoulder at all and reads as
    # a traffic cone under the head.
    COAT_HALF = 40.0
    # Where the arms attach and how far out the hands sit. ARM_REACH has to clear the
    # hem comfortably, or the whole sleeve stays inside the coat silhouette -- navy
    # sleeve on navy coat, and all that is left of the arm is the cuff and the hand,
    # which stack into something that reads as a hat sitting on the keys.
    # Shoulder pulled in to 29: at 36 the sleeve root landed exactly on top of the
    # front hair locks, and since the arms are drawn last the sleeve cut each lock in
    # half -- hair above it, hair below it, and nothing reading as one strand. Tucked
    # in, the sleeve root sits over the coat instead, and the lock *tips* end under
    # the sleeve, which is how hair over a shoulder is supposed to look.
    ARM_SHOULDER = 29.0
    ARM_SHOULDER_Y = 112.0
    ARM_REACH = 45.0
    # Front locks: the numbers, and which side of the arms they are drawn on. The two
    # go together -- locks long enough to reach the cuff have to be behind the sleeve,
    # and locks drawn in front of it have to stop above the hand (see _FRONT_LOCKS_SHORT).
    FRONT_LOCKS = _FRONT_LOCKS
    # How much of the head's forward slump the locks do NOT follow. The head drops 11
    # when she falls asleep (`body_dy` 3 plus another 8 of slump) but the shoulders only
    # drop the 3, so locks pinned to the head dive 8 units into the arm -- which lands
    # both tips on the corner of the gold cuff. At 8 they follow the shoulders instead,
    # which is also what hair resting on an arm does. It only matters because the tips
    # are in front of the sleeve; behind it they would just sink further out of sight.
    LOCKS_SLUMP_LIFT = 8.0

    @classmethod
    def draw(cls, p: QPainter, pose: Pose) -> None:
        body_dy = pose.breath * 1.0 + pose.slump * 3.0
        cx = 100.0 + pose.look_x * 5.0
        cy = cls.HEAD_CY + pose.look_y * 3.0 + body_dy + pose.slump * 8.0 - pose.surprise * 2.0

        # Back hair goes behind the keyboard so the long locks can run off the
        # bottom; everything else sits in front of it.
        cls._back_hair(p, pose, cx, cy)
        cls.draw_keyboard(p)
        cls._coat(p, body_dy)
        # Arms before the locks, and the head after them: the sleeve has to come out
        # from under the hair, and the head is what hides the locks' roots.
        cls._arms(p, pose, body_dy)
        cls._front_locks(p, pose, cx, cy)
        cls._head(p, pose, cx, cy)
        if pose.zzz >= 0.0:
            cls.draw_zzz(p, pose.zzz, cx + 20.0, cy - 30.0)

    # -- hair -------------------------------------------------------------

    @classmethod
    def _back_hair(cls, p: QPainter, pose: Pose, cx: float, cy: float) -> None:
        s = pose.tail
        shapes = [_disc(cx + x, cy + y, r) for x, y, r in _BACK_HAIR]
        # the sway rides on the tips only, where real hair moves
        shapes.append(_disc(cx - 38.0 + s * 5.0, cy + 66.0, 14.0))
        shapes.append(_disc(cx + 40.0 + s * 6.0, cy + 66.0, 14.0))
        merged(p, shapes, INK, _hair_fill(cy - 68.0), STROKE)

    @classmethod
    def _front_locks(cls, p: QPainter, pose: Pose, cx: float, cy: float) -> None:
        """The pair that frames the face and lies over the shoulders. Drawn after the
        coat and the arms: hair hangs in front of clothing, and its root is hidden by
        the head, which comes next.

        Everything about where the tips stop is in `_FRONT_LOCKS`. One rule that is not
        in the numbers: a tip must never run *past* the sleeve on the inner side. An
        early version ran to y=149 aimed inward, and since the arms were drawn last the
        strand went behind the sleeve at the shoulder and came back out below it, which
        reads as hair skewered by an arm.

        The sway rides on the tips only, and only on the lower pair -- the upper two
        are the roots of the same strands and a root that moves is a wig slipping.
        """
        s = pose.tail
        ly = cy - pose.slump * cls.LOCKS_SLUMP_LIFT
        shapes = [
            _lock(cx + dx, ly + dy + s * sdy, w, h, rot + s * srot)
            for dx, dy, w, h, rot, sdy, srot in cls.FRONT_LOCKS
        ]
        merged(p, shapes, INK, _hair_fill(cy - 40.0), STROKE)

    @classmethod
    def _bangs(cls, p: QPainter, cx: float, cy: float) -> None:
        """Soft scalloped fringe. The bottom edge is four shallow lobes -- a
        zigzag polyline here reads as a crown of spikes, not as hair."""
        top = cy - cls.HEAD_RY
        b = QPainterPath(QPointF(cx - 39.0, cy - 10.0))
        b.cubicTo(QPointF(cx - 43.0, top - 2.0), QPointF(cx - 22.0, top - 14.0),
                  QPointF(cx + 2.0, top - 13.0))
        b.cubicTo(QPointF(cx + 26.0, top - 14.0), QPointF(cx + 43.0, top - 2.0),
                  QPointF(cx + 39.0, cy - 10.0))
        for c1, c2, end in (
            ((30.0, -22.0), (27.0, -18.0), (21.0, -5.0)),
            ((15.0, -19.0), (13.0, -22.0), (7.0, -11.0)),
            ((1.0, -24.0), (-4.0, -24.0), (-9.0, -8.0)),
            ((-15.0, -21.0), (-19.0, -21.0), (-25.0, -5.0)),
        ):
            b.cubicTo(QPointF(cx + c1[0], cy + c1[1]), QPointF(cx + c2[0], cy + c2[1]),
                      QPointF(cx + end[0], cy + end[1]))
        b.closeSubpath()
        p.setPen(pen(INK, STROKE))
        p.setBrush(_hair_fill(top - 14.0))
        p.drawPath(b)

    @classmethod
    def _ahoge(cls, p: QPainter, flick: float, cx: float, cy: float) -> None:
        """One strand standing straight up, tapered to a point.

        Filled rather than stroked: a constant-width stroked curve with a round cap
        reads as a bent wire or a fishing hook, not as hair. It leans away from the
        hat (which is anchored right of centre) so the two do not collide.
        """
        sx, sy = cls.AHOGE_SCALE_X, cls.AHOGE_SCALE_Y
        k = (sx * sy) ** 0.5
        p.save()
        p.translate(cx - 9.0 * sx, cy - cls.HEAD_RY - 6.0)
        p.rotate(cls.AHOGE_LEAN)
        p.scale(sx, sy)

        tipx = -8.0 - flick * 4.0
        tipy = -21.0 - flick * 3.0
        strand = QPainterPath(QPointF(-3.2, 0.0))
        strand.cubicTo(QPointF(-5.0, -11.0), QPointF(tipx + 1.0, tipy + 5.0),
                       QPointF(tipx, tipy))
        strand.cubicTo(QPointF(3.0, tipy + 8.0), QPointF(4.2, -10.0), QPointF(3.2, 0.0))
        strand.closeSubpath()
        # Pen width divided by the scale: the outline weight is a property of the
        # drawing, not of the strand, and every other line on this character is 2-3
        # units. A scaled-up 2.6 comes out as a fat cartoon border on one element only.
        p.setPen(pen(INK, 2.6 / k))
        p.setBrush(QBrush(HAIR_W))
        p.drawPath(strand)
        p.restore()

    # -- hat --------------------------------------------------------------

    @classmethod
    def _hat(cls, p: QPainter, tip: float, cx: float, cy: float) -> None:
        """Perched on the hair, tilted, not balanced above the head.

        A full-height top hat does not fit: the hair already tops out near y=2 on
        a 180px canvas, so the brim has to cut into the hair and the crown has to
        stay short. The tilt is small for the same reason -- rotating a tall crown
        swings its far corner off the top of the canvas.
        """
        sx, sy = cls.HAT_SCALE_X, cls.HAT_SCALE_Y
        k = (sx * sy) ** 0.5
        ax, ay = cls.HAT_ANCHOR
        p.save()
        p.translate(cx + ax, cy + ay)
        p.rotate(cls.HAT_ROT + tip * 8.0)
        p.scale(sx, sy)

        if cls.HAT_FEATHER:
            # Right side, away from the ahoge: both are white and both sweep up, so
            # on the same side they fuse into one big blade.
            feather = QPainterPath(QPointF(8.0, -12.0))
            feather.cubicTo(QPointF(24.0, -28.0), QPointF(38.0, -22.0),
                            QPointF(41.0, -6.0))
            feather.cubicTo(QPointF(27.0, -13.0), QPointF(16.0, -9.0),
                            QPointF(8.0, -7.0))
            feather.closeSubpath()
            p.setPen(pen(INK, 2.0 / k))
            p.setBrush(QBrush(WHITE))
            p.drawPath(feather)

        # Crown slightly wider at the top than the base, so it reads as a top hat
        # rather than a box. All the gold sits in the bottom third: an ornament band
        # across the middle splits the navy into two thin strips and the whole thing
        # comes out looking like a bookmark clipped to her head.
        crown = QPainterPath(QPointF(-16.0, -2.0))
        crown.lineTo(QPointF(-17.5, -31.0))
        crown.quadTo(QPointF(0.0, -34.5), QPointF(17.5, -31.0))
        crown.lineTo(QPointF(16.0, -2.0))
        crown.closeSubpath()
        p.setPen(pen(INK, 2.6 / k))
        p.setBrush(_grad(0.0, -34.0, 0.0, -2.0, NAVY_L, NAVY))
        p.drawPath(crown)

        p.setBrush(QBrush(NAVY_D))
        p.drawRoundedRect(QRectF(-25.0, -2.5, 50.0, 8.0), 4.0, 4.0)     # brim

        cls._crown(p, k)

        # Ribbon on the brim's left, clear of the coronet above it.
        p.setPen(pen(INK, 2.0 / k))
        p.setBrush(QBrush(GEM))
        for side in (-1.0, 1.0):
            bow = QPainterPath(QPointF(-18.0, 1.5))
            bow.lineTo(QPointF(-18.0 + side * 9.0, -3.5))
            bow.lineTo(QPointF(-18.0 + side * 8.0, 6.5))
            bow.closeSubpath()
            p.drawPath(bow)
        p.setBrush(QBrush(GOLD_L))
        p.drawEllipse(QRectF(-21.0, -1.0, 6.0, 6.0))

        drop = QPainterPath(QPointF(15.0, 5.0))
        drop.cubicTo(QPointF(20.0, 11.0), QPointF(19.0, 17.0), QPointF(15.0, 17.0))
        drop.cubicTo(QPointF(11.0, 17.0), QPointF(10.0, 11.0), QPointF(15.0, 5.0))
        p.setPen(pen(INK, 1.8 / k))
        p.setBrush(QBrush(GEM))
        p.drawPath(drop)
        p.restore()

    @classmethod
    def _crown(cls, p: QPainter, k: float = 1.0) -> None:
        """Gold coronet round the base of the crown -- the silhouette cue that keeps
        the hat from reading as a generic topper. Teeth point up into the navy so the
        gold reads as a crown sitting in the hat, not as a stripe painted on it."""
        # The base strip matters: a zigzag closed straight back along its own start
        # line has no body, and the coronet renders as a row of gold studs.
        band = QPainterPath(QPointF(-17.0, -2.0))
        band.lineTo(QPointF(-17.0, -8.0))
        for i, x in enumerate((-16.6, -8.3, 0.0, 8.3, 16.6)):
            band.lineTo(QPointF(x, -8.0 - (10.0 if i % 2 == 0 else 3.5)))
            band.lineTo(QPointF(x + 4.1, -8.0 - (3.5 if i % 2 == 0 else 10.0)))
        band.lineTo(QPointF(17.0, -2.0))
        band.closeSubpath()
        p.setPen(pen(INK, 2.0 / k))
        p.setBrush(_grad(0.0, -19.0, 0.0, -2.0, GOLD_L, GOLD))
        p.drawPath(band)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(GEM))
        for x in (-12.5, 0.0, 12.5):
            p.drawEllipse(QRectF(x - 2.1, -8.0, 4.2, 4.2))

    # -- body -------------------------------------------------------------

    @classmethod
    def _coat(cls, p: QPainter, body_dy: float) -> None:
        """Shoulders at the top, fitted towards the hem.

        The hem is narrower than the shoulders on purpose: it is what leaves room
        for the sleeves to run down outside the torso instead of inside it.
        """
        top = 96.0 + body_dy
        hw = cls.COAT_HALF
        sy = top + 11.0
        hem = hw * 0.78
        # Hem stops at 132, just shy of the keyboard's top edge (134): the coat is
        # drawn in front of the keys, so a longer hem covers them.
        coat = QPainterPath(QPointF(100.0 - hw * 0.30, top))
        coat.quadTo(QPointF(100.0 - hw, top + 1.0), QPointF(100.0 - hw, sy))
        coat.cubicTo(QPointF(100.0 - hw, sy + 8.0),
                     QPointF(100.0 - hem, 120.0), QPointF(100.0 - hem, 132.0))
        coat.lineTo(QPointF(100.0 + hem, 132.0))
        coat.cubicTo(QPointF(100.0 + hem, 120.0),
                     QPointF(100.0 + hw, sy + 8.0), QPointF(100.0 + hw, sy))
        coat.quadTo(QPointF(100.0 + hw, top + 1.0), QPointF(100.0 + hw * 0.30, top))
        coat.closeSubpath()
        p.setPen(pen(INK, 2.8))
        p.setBrush(_grad(100.0, top, 100.0, 132.0, NAVY_L, NAVY_D))
        p.drawPath(coat)

        shirt = QPainterPath(QPointF(100.0, top + 2.0))
        shirt.lineTo(QPointF(100.0 - hem * 0.42, 132.0))
        shirt.lineTo(QPointF(100.0 + hem * 0.42, 132.0))
        shirt.closeSubpath()
        p.setPen(pen(INK, 2.0))
        p.setBrush(QBrush(WHITE))
        p.drawPath(shirt)

        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(GOLD))
        for y in (120.0, 128.0):
            p.drawEllipse(QRectF(97.4, y, 5.2, 5.2))

        cls._cravat(p, top + 8.0)

    @classmethod
    def _cravat(cls, p: QPainter, y: float) -> None:
        p.setPen(pen(INK, 2.2))
        for side in (-1.0, 1.0):
            wing = QPainterPath(QPointF(100.0, y + 3.0))
            wing.lineTo(QPointF(100.0 + side * 17.0, y - 4.0))
            wing.lineTo(QPointF(100.0 + side * 15.0, y + 11.0))
            wing.closeSubpath()
            p.setBrush(QBrush(GEM))
            p.drawPath(wing)
        p.setBrush(_grad(95.0, y, 105.0, y + 10.0, GOLD_L, GOLD))
        p.drawEllipse(QRectF(95.0, y, 10.0, 10.0))

    @classmethod
    def _arms(cls, p: QPainter, pose: Pose, body_dy: float) -> None:
        for side, lift in ((-1.0, pose.paw_l), (1.0, pose.paw_r)):
            sx = 100.0 + side * cls.ARM_SHOULDER
            sy = cls.ARM_SHOULDER_Y + body_dy
            hx = 100.0 + side * (cls.ARM_REACH + lift * 4.0)
            hy = 146.0 - lift * 11.0
            cls._limb(p, sx, sy, hx, hy)

    @classmethod
    def _limb(cls, p: QPainter, sx: float, sy: float, hx: float, hy: float) -> None:
        """Sleeve, gold cuff, round white glove.

        What carries the arm is the *sleeve*, not the hand: a long taper in the light
        navy so it separates tonally from the coat, running outside the coat
        silhouette. With that reading correctly the hand can be as simple as a circle
        -- and simple is better here, because an earlier version gave it an ellipse
        with three knuckle lobes merged onto the leading edge, and at 20px across the
        lobes did not read as fingers. They just made the outline lumpy, which looks
        like a mistake rather than like a hand.

        Three tones in a row, and each boundary is doing a job: navy sleeve, gold
        cuff, white glove. The cuff used to be white, which was wrong twice over --
        the reference has gold trim there, and a white band butted against a white
        glove merges into one pale blob with no wrist in it.
        """
        ang = math.atan2(hy - sy, hx - sx)
        nx, ny = -math.sin(ang), math.cos(ang)
        wx = hx - math.cos(ang) * 11.0
        wy = hy - math.sin(ang) * 11.0

        sleeve = QPainterPath(QPointF(sx + nx * 8.5, sy + ny * 8.5))
        sleeve.lineTo(QPointF(wx + nx * 5.5, wy + ny * 5.5))
        sleeve.lineTo(QPointF(wx - nx * 5.5, wy - ny * 5.5))
        sleeve.lineTo(QPointF(sx - nx * 8.5, sy - ny * 8.5))
        sleeve.closeSubpath()
        p.setPen(pen(INK, 2.6))
        p.setBrush(_grad(sx, sy, wx, wy, NAVY_L, NAVY))
        p.drawPath(sleeve)

        # Cuff first, so the glove overlaps it and the glove looks like it is on the
        # end of the sleeve rather than floating past it.
        p.save()
        p.translate(wx, wy)
        p.rotate(math.degrees(ang))
        p.setPen(pen(INK, 2.0))
        p.setBrush(_grad(-3.0, 0.0, 3.0, 0.0, GOLD_L, GOLD))
        p.drawRoundedRect(QRectF(-2.4, -7.8, 6.2, 15.6), 2.4, 2.4)
        p.restore()

        # A round glove, wider than the cuff so it clearly sits on the end of the arm
        # rather than beside it. Gradient runs top-light to bottom-shadow, which is
        # what keeps a plain circle reading as a ball instead of a flat disc -- and on
        # a white glove the gradient is the *only* thing doing that, since a white
        # highlight on white has nothing to be lighter than.
        r = 9.5
        p.setPen(pen(INK, 2.6))
        p.setBrush(_grad(hx, hy - r, hx, hy + r, GLOVE, GLOVE_D))
        p.drawEllipse(QRectF(hx - r, hy - r, r * 2.0, r * 2.0))

    # -- head -------------------------------------------------------------

    @classmethod
    def _head(cls, p: QPainter, pose: Pose, cx: float, cy: float) -> None:
        p.setPen(pen(INK, 2.8))
        p.setBrush(QBrush(SKIN))
        p.drawEllipse(QRectF(cx - cls.HEAD_RX, cy - cls.HEAD_RY,
                             cls.HEAD_RX * 2.0, cls.HEAD_RY * 2.0))

        cls._bangs(p, cx, cy)
        cls._eyes(p, pose, cx, cy)
        cls._blush(p, pose, cx, cy)
        cls._mouth(p, pose, cx, cy)
        cls._ahoge(p, pose.ear_l, cx, cy)
        cls._hat(p, pose.ear_r, cx, cy)

    @classmethod
    def _blush(cls, p: QPainter, pose: Pose, cx: float, cy: float) -> None:
        alpha = int(70 + pose.surprise * 110)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(BLUSH_C.red(), BLUSH_C.green(), BLUSH_C.blue(), alpha)))
        for side in (-1.0, 1.0):
            p.drawEllipse(QRectF(cx + side * 26.0 - 9.0, cy + 12.0, 18.0, 9.0))

    @classmethod
    def _eyes(cls, p: QPainter, pose: Pose, cx: float, cy: float) -> None:  # pragma: no cover
        raise NotImplementedError

    @classmethod
    def _mouth(cls, p: QPainter, pose: Pose, cx: float, cy: float) -> None:  # pragma: no cover
        raise NotImplementedError


class FurinaSkin(FurinaBase):
    """Q-head Furina: dopey black bean eyes, oversized top hat, big ahoge.

    The hat and the ahoge grow by being re-aimed rather than just scaled up, because
    there is no room above the head to grow into (see HAT_SCALE on FurinaBase):

    - The hat goes up about a quarter on both axes, with the width very slightly ahead.
      It has to stay close to square: a first pass pushed the width to 1.34 against 1.2
      of height, and a top hat wider than it is tall stops being a top hat and becomes
      a cake box.
    - The head sits 4 lower, buying the crown that much more room. Any lower and it
      starts covering the cravat, which is half the reason the silhouette reads as her.
    - The ahoge leans 30 degrees and stretches along its length only. Standing it up
      taller ran it off the canvas; fattening it to match turned it into a white blade
      that looked like a feather stuck in her hair.
    """

    KEY = "furina"
    NAME = "芙宁娜"
    HEAD_RX = 39.0
    HEAD_RY = 40.0
    HEAD_CY = 70.0
    # Wider crop than the default: the big hat puts the head box well right of centre.
    ICON_CROP = (34.0, 0.0, 132.0)
    # 14 degrees, not the 20 the smaller hat used. The ceiling here is not taste, it is
    # the canvas: tilting the crown swings its far top corner up, and `tip` adds another
    # 8 degrees on top of HAT_ROT during a head-tip pose while `surprise` lifts the whole
    # head 2 -- so the worst frame is roughly 6 units higher than the resting one, which
    # is all the margin there is.
    HAT_ROT = 14.0
    HAT_SCALE_X = 1.26
    HAT_SCALE_Y = 1.24
    HAT_ANCHOR = (19.0, -29.0)
    AHOGE_SCALE_X = 1.12
    AHOGE_SCALE_Y = 1.45
    AHOGE_LEAN = -30.0

    @classmethod
    def _eyes(cls, p: QPainter, pose: Pose, cx: float, cy: float) -> None:
        """Plain black beans. No iris, no glint -- the blankness is the whole
        joke. A glance slides the entire bean instead of a pupil inside a
        sclera."""
        open_amt = max(0.0, min(1.0, pose.eye_open))
        for side in (-1.0, 1.0):
            ex = cx + side * 17.0 + pose.look_x * 4.0
            ey = cy + 3.0 + pose.look_y * 3.0

            if open_amt < 0.25:
                p.setBrush(Qt.NoBrush)
                p.setPen(pen(INK, 3.0))
                lid = QPainterPath(QPointF(ex - 8.0, ey + 2.0))
                lid.quadTo(QPointF(ex, ey - 5.0), QPointF(ex + 8.0, ey + 2.0))
                p.drawPath(lid)
                continue

            r = 7.6 * (1.0 + pose.surprise * 0.3)
            ry = r * open_amt
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(INK))
            p.drawEllipse(QRectF(ex - r, ey - ry, r * 2.0, ry * 2.0))
            if pose.surprise > 0.3:
                p.setBrush(QBrush(QColor(255, 255, 255, 200)))
                p.drawEllipse(QRectF(ex - r * 0.5, ey - ry * 0.6, r * 0.42, ry * 0.42))

    @classmethod
    def _mouth(cls, p: QPainter, pose: Pose, cx: float, cy: float) -> None:
        gape = max(0.0, min(1.0, pose.mouth))
        my = cy + 22.0
        if gape > 0.1:
            h = 4.0 + gape * 13.0
            w = 4.5 + gape * 4.5
            p.setPen(pen(INK, 2.0))
            p.setBrush(QBrush(LIP))
            p.drawEllipse(QRectF(cx - w, my - h * 0.3, w * 2.0, h))
            return
        p.setPen(pen(INK, 2.2))
        p.setBrush(Qt.NoBrush)
        for side in (-1.0, 1.0):
            lip = QPainterPath(QPointF(cx, my + 1.0))
            lip.quadTo(QPointF(cx + side * 3.0, my + 4.0), QPointF(cx + side * 6.0, my))
            p.drawPath(lip)
