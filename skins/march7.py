"""March 7th, chibi, in the derp idiom of the Furina skin.

Derp means: oversized head, solid bean eyes with no sclera, and the whole hair mass
under one outline via `merged()`. What is *not* shared is the shape language --
Furina's hair is round lobes, hers is pointed wisps, and drawing hers with lobes
(which the first version did) produced a pink poodle that could have been anyone.

The recognition cues, in the order they carry:

  1. pink hair in sharp tapered locks, with a deep side parting
  2. the black choker with a brass buckle, right under the chin
  3. the white jacket with a pale-blue cape collar
  4. the white flower on the chest
  5. eyes: violet at the top, cyan at the bottom

Only 5 is compromised by the derp treatment -- a bean eye has no iris to put a
gradient in -- so it survives as a cyan crescent inside an otherwise solid bean.

Pose reinterpretation: `ear_l` bounces the front wisp of the fringe, `ear_r` flutters
the hair ribbon, `tail` sways the hanging locks and the ahoge.

There used to be a second, short-haired skin here and this file was its base class,
with the long version as a subclass that swapped tables. The short one is gone, so the
tables are back in the class body -- but they are still tables, and the drawing code
still reads every number out of them, which is what keeps the next variant cheap.
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

# Line art in the reference is a warm dark plum, not black -- black outlines on pink
# go cold and the whole thing stops looking like the same palette.
INK = QColor("#57394F")
SKIN = QColor("#FDEDE4")
# Sampled off skins/ref/4.webp rather than eyeballed. The span is the whole point:
# the lit hair there is all but white (#FCF4F7 on the crown, #F8DDEB in the fringe
# shadow) and the underside is a genuinely saturated rose (#C3698E). An earlier pass
# picked three tones that all sat in the middle of that range, and the result read as
# flat bubblegum -- her hair is pale, with the pink only arriving at the tips.
HAIR = QColor("#F8DFEC")
HAIR_L = QColor("#FCF2F7")
HAIR_D = QColor("#CD6D96")
# For the hair that lies *on the face* -- fringe and the two strands down the cheeks.
# Once the mass went pale, HAIR (#F8DFEC) and SKIN (#FDEDE4) were within a couple of
# values of each other, so the fringe stopped being a shape and became a bare ink
# zigzag on her forehead. Hair in front of the face is shaded anyway, so taking it a
# few steps pinker is both the fix and the correct reading.
HAIR_M = QColor("#EEBDD5")
WHITE = QColor("#FDFDFF")
CREAM = QColor("#EFF3F9")
BLUE_P = QColor("#C4E2F6")
BLUE = QColor("#82C6EA")
BLUE_D = QColor("#4A8FC4")
CHOKER = QColor("#342B35")
BRASS = QColor("#C9A15E")
BRASS_L = QColor("#E8D19B")
CYAN = QColor("#5FD2F0")
VIOLET = QColor("#4A2F5E")
BLUSH_C = QColor("#F48FA6")
LIP = QColor("#C9566E")

STROKE = 3.0

# THE ONE RULE FOR THIS HAIR, learned the hard way over four rewrites: there is
# exactly ONE stroked hair outline on this character, and it is the silhouette of the
# whole mass. Everything else inside the hair is told apart by TONE, never by a line.
#
# What forced it: the version before this drew five separately-outlined hair shapes --
# back mass, two cheek strands, fringe, two shoulder strands, a stray cowlick -- all
# overlapping each other inside one pink area. Every one carried its own ink border, so
# the inside of her hair was a tangle of arcs crossing at T-junctions, with the mass's
# concave notches reading as gashes cut into it. It does not matter how well each shape
# is drawn: n outlined shapes stacked in the same colour region produce n*(n-1) places
# for two lines to cross, and a crossing line is the one thing a viewer reads as a
# mistake rather than as detail.
#
# So: `_hair` merges every strand that hangs (including the cowlick) into a single
# silhouette. `_face_hair` is the one exception, and it is stroked only along the edges
# that border *skin*, where a line is carrying real information.
#
#   (root x, root y, width, length, rotation)
#
# Rotation is a Qt rotate() of a lock whose tip starts at +y, so the tip direction is
# (-sin r, cos r) in screen coordinates: 0 is straight down, POSITIVE swings the tip
# left, negative swings it right, +-90 is horizontal and 180 is straight up. Getting
# this backwards is what killed the last two attempts -- every "outward" lock was
# aimed inward across the skull, so the tips vanished inside the mass and all that was
# left of the silhouette was the roots.
#
# Roots sit *inside* the skull on purpose: the discs cover them, so only the pointed
# half of each lock reaches the outline.
# Every rotation is small -- 8 to 20 degrees. Fanned out to 162 they aimed each strand
# radially away from the skull like the spokes of a wheel, and a head of radial spokes
# is a starburst, not a hairstyle. Hair falls DOWN, and flares at the tips only.
#
# Two strands a side, not six. Six tips means six notches in the silhouette, and a row
# of notches along an edge is a saw blade -- at 200 units wide there is no room for
# feathering to read as anything else. One long strand plus one shorter one outside it
# gives a single notch per side, which reads as two strands, which is what is wanted.
#
# WHAT THE ARMS DO TO A LONG LOCK, because it is why the hair is drawn in front of them.
# An earlier version hung these locks to y=129 with the arms in front, and none of it
# showed: the sleeves run from the shoulders at y=112 down to the hands at y=146,
# covering x 51..67 and 133..149 the whole way, so every lock aimed at the floor ended
# up behind an arm and the hair read as a chin-length bob no matter how long it was.
# Measured off the render, not guessed.
#
# Aiming the locks *outward* past the sleeves instead (rotations of 23 and 30) does clear
# them, but the tips land out at x=47 and x=158 with the mass fattened to match, and a
# wider dome is not longer hair -- it read as a bigger head. Worse, the outer lock merged
# into the temple piece and the notch between the two strands disappeared, so it lost the
# one thing that made it a hairstyle rather than a shape.
#
# So the arms are drawn first and the whole mass goes in front of them -- one pass, one
# outline, nothing split. The sleeves emerge from under the hair, which is what arms do.
# The cost is that a lock can cut a sleeve in half, and a sleeve cut in half turns the
# hand into a ball floating beside her. That is a function of WHERE it crosses: over the
# upper arm just below the shoulder it reads as hair lying on a sleeve, but over the
# forearm near the cuff it reads as an amputation. Hence every tip stops at or above
# y=126, clear of the cuffs at y=135 and of the keyboard's top edge at 134 (the keyboard
# is drawn first, so a lock that reached it would be painted over the keys).
#
# Tips, worked out rather than eyeballed, because a couple of units either way is the
# difference between a visible tip and one behind a sleeve:
#
#   L1  (65.5, 125.4)  the long one, down the front of the left shoulder
#   L2  (47.3, 108.9)  shorter and outboard, so the gap between them is a notch
#   R1  (132.6, 117.6) 8 higher than L1 -- this is the lopsidedness
#   R2  (150.0, 103.7)
#
# The parting is right of centre, so more hair sweeps left: the left side gets the
# thicker lock and the tip that reaches lowest. Symmetry reads as a wig, and a couple of
# units of it is not enough to see -- 8 is.
#
# It deliberately does NOT fall across the middle of her chest, which is the strongest
# long-hair cue there is at this size. That lands squarely on the white flower and the
# pale-blue cape collar, cues 4 and 3. The inner locks are held at x=64 and x=134 so both
# stay visible; the flower sits at x=82, just inboard of the left one.
_HAIR_FALL = (
    (-27.0, 10.0, 24.0, 48.0, 9.0),
    (-37.0, 2.0, 17.0, 42.0, 22.0),
    # right side, deliberately not a mirror -- symmetry reads as a wig
    (27.0, 10.0, 21.0, 40.0, -8.0),
    (37.0, 0.0, 16.0, 38.0, -20.0),
)
# The ahoge, as (x, y, w, h, rot) in the same units -- rot near 180 points the tip UP.
#
# It goes through `merged()` with everything else, which is the only way it can exist on
# this character. An earlier pass drew it as its own stroked lock and that put a closed
# ink loop in the middle of the pink for the sake of one bump in the outline. Merged, its
# base is not drawn at all: the crown oval swallows it, the two concave notches where it
# leaves the dome are exactly the notches a strand standing off a head actually has, and
# the needle tip is the same `_lock` shape as every other strand on her.
#
# Rooted just right of the parting (which is near cx+15) and leaning left across it, away
# from the ribbon at cx+38 -- both are silhouette features and on the same side they fuse
# into one lump.
#
# ROOTED RIGHT OF THE PEAK, LEANING LEFT. Which side it leaves the dome from is the whole
# difference between a strand and a smudge. Rooted at cx+12 it exited just left of the
# crown's peak, where the dome is already falling away leftwards at about the angle the
# strand itself leans -- so its left edge ran nearly tangent to the outline and the two
# 6-wide ink rims pinched together into a blob with a sliver of pink trapped inside. From
# cx+20 it exits the right flank instead and crosses the outline at a healthy angle, which
# leaves a clean V-notch on both sides. Pushed further out to cx+25 the same thing happens
# in mirror image on the right edge. The rule underneath: an added shape only reads as
# separate where its edges MEET the silhouette across an angle, and near-tangent is the
# one arrangement guaranteed not to have one.
#
# SO IT LEANS, and the lean is not a stylistic choice -- it is the only way to buy length.
# The budget above the dome is 14 units and that is all there is: `cy` bottoms out at 62
# (look_y -1, breath -1 and surprise 1 all at once), art coordinates survive only to -5
# because that is the MARGIN, and `merged` strokes its outline pass with a pen of
# STROKE*2, which juts 3 more units outside the path. A strand standing straight up can
# therefore only show about 11 units of itself, which is its own width, which is an ear.
# At 40 degrees off vertical the same 14 units of headroom expose 15 units of strand, and
# 15 against a 9-wide base is a wisp. Two earlier tries came in at cy-69 and cy-64 and
# both got sheared off flat against the top of the frame in precisely the poses where she
# looks up -- which are the poses someone is most likely to be watching.
_HAIR_AHOGE = (20.0, -40.0, 9.0, 27.0, 142.0)
# Skull volume, as (x, y, rx, ry). The bottom of the widest one is what closes the
# silhouette between the two hanging strands, and it sits at cy+32 -- behind the jaw,
# above the collar, so the join never shows.
#
# The crown is ONE oval, not a pile of circles. Two overlapping circles always leave a
# concave notch where their edges cross, and the old crown had five of them: the notches
# came out as scallops around the top of her head, so the silhouette read as a row of
# bubbles rather than as a head. An oval has no notch to leave. The two temple pieces are
# still circles because their joins fall low down at the sides, where the hanging strands
# are and where a notch is a parting between strands rather than a dent in her skull.
#
# Same overall width as the short-haired version this replaces (x 43..156), because the
# length is supposed to come from the locks and a wider dome is just a bigger head. The
# temple pieces are dropped 2 units and the right one is a shade smaller than the left,
# which is where the unevenness starts.
_HAIR_CROWN = (
    (0.0, -10.0, 42.0, 40.0),
    (-32.0, 10.0, 25.0, 26.0), (32.0, 8.0, 24.0, 25.0),
)


def _grad(x0: float, y0: float, x1: float, y1: float, c0: QColor, c1: QColor) -> QBrush:
    g = QLinearGradient(QPointF(x0, y0), QPointF(x1, y1))
    g.setColorAt(0.0, c0)
    g.setColorAt(1.0, c1)
    return QBrush(g)


def _hair_fill(top: float, span: float = 115.0) -> QBrush:
    """The ONE fill for every piece of hair on this character. Pass the same `top`.

    `span` is how far down the deep rose is reached, and it has to track the length of
    the hair: the stops are fractions of the span, so lengthening the locks by 40 units
    without stretching the span saturates the tips half way down and the last third comes
    out as a flat rose block. Use `cls._fill(cy)` rather than calling this directly --
    that is what keeps the two masses sampling the same gradient.

    There used to be a second, deeper gradient for the hair lying on the face. That is
    what produced "颜色不一致，一个盖着一个": the fringe covers the top half of the
    skull, so a fringe two shades deeper than the mass behind it drew a hard-edged
    mid-pink cap over a pale head of hair, and the unstroked boundary between them --
    which was supposed to be invisible -- was the most conspicuous line on her.

    The reference settles it. Zoom in on skins/ref/4.webp and the crown, the fringe and
    the side locks are all the *same* pale pink; nothing there is told apart by a block
    of tone. What separates them is (a) the ink line where hair meets skin and (b) thin
    rose strand lines fanning out of the parting. So there is one gradient, both masses
    sample it at the same `top`, and at any given height they come out identical -- the
    boundary cannot show because there is nothing there to show.

    Vertical range, all of it pink (HAIR_L is not in here: #FCF2F7 against SKIN #FDEDE4
    is the same tone to the eye, and hair filled with it reads as scalp -- that was the
    bald head, twice):

      crown      HAIR    pale, the lit top of the head
      brow-down  HAIR_M  reached by 0.40, so the fringe's edge is never confusable
                         with the skin it sits on
      tips       HAIR_D  rose, only at the ends
    """
    g = QLinearGradient(QPointF(0.0, top), QPointF(0.0, top + span))
    g.setColorAt(0.0, HAIR)
    g.setColorAt(0.14, HAIR)
    g.setColorAt(0.40, HAIR_M)
    g.setColorAt(1.0, HAIR_D)
    return QBrush(g)


# The parting is at roughly (cx+9, cy-57) -- high on the skull and right of centre.
# Nothing computes from that: the strand roots in HAIR_STRANDS and the peak of the
# fringe arch in FRINGE_PEAK_X are each placed by hand to agree with it, because both
# want a slightly different offset from it. Moving the parting means moving both.


def _disc(x: float, y: float, rx: float, ry: float) -> QPainterPath:
    path = QPainterPath()
    path.addEllipse(QRectF(x - rx, y - ry, rx * 2.0, ry * 2.0))
    return path


def _lock(x: float, y: float, w: float, h: float, rot: float) -> QPainterPath:
    """A wisp: wide at the root, needle-pointed at the tip.

    The tip is a real corner, not a rounded end -- that is the entire difference
    between this hairstyle and a cloud, and rounding it by even a couple of pixels
    puts the poodle back.
    """
    path = QPainterPath(QPointF(-w * 0.5, 0.0))
    path.cubicTo(QPointF(-w * 0.54, h * 0.44), QPointF(-w * 0.30, h * 0.84),
                 QPointF(0.0, h))
    path.cubicTo(QPointF(w * 0.34, h * 0.82), QPointF(w * 0.56, h * 0.40),
                 QPointF(w * 0.5, 0.0))
    path.closeSubpath()
    t = QTransform()
    t.translate(x, y)
    t.rotate(rot)
    return t.map(path)


class March7Skin(Skin):
    KEY = "march7"
    NAME = "三月七"
    OUTLINE = INK
    # Not the head box -- the whole figure above the keyboard, measured off a render:
    # art x 40..158, y 3..127. The head box alone cropped the ahoge off at the top and the
    # locks off at the bottom, and a tray icon of a beheaded ahoge is worse than no ahoge.
    # 128 square with 2 units of slack top and bottom; the head comes out smaller than the
    # other skins' icons as a result, which is the price of the hair being the silhouette.
    ICON_CROP = (35.0, 1.0, 128.0)

    HEAD_CY = 68.0
    HEAD_RX = 38.0
    HEAD_RY = 39.0
    COAT_HALF = 40.0
    ARM_SHOULDER = 36.0
    ARM_SHOULDER_Y = 112.0
    # Pulled in from 50 so the lifted hand -- which rises to y=125.5 on a keypress -- is
    # not underneath the long lock's tip.
    ARM_REACH = 46.0

    # -- hair geometry, all of it, as data -------------------------------------
    #
    # Every number the hairstyle is made of lives here so a variant can be a subclass
    # that swaps tables instead of a copy of the drawing code. The rules the drawing
    # code enforces -- one outline, one gradient, tone-not-line inside the mass -- are
    # not negotiable per skin, so they stay in the methods; only the shapes are data.
    HAIR_FALL = _HAIR_FALL
    HAIR_CROWN = _HAIR_CROWN
    HAIR_AHOGE = _HAIR_AHOGE
    # Gradient origin and length, relative to cy. See _hair_fill. The span is 126 and not
    # the 115 the short hair used: the mass reaches ~62 below cy now against ~50 before,
    # so the rose has to arrive later or the bottom third comes out as one flat saturated
    # block instead of a taper.
    HAIR_GRAD_TOP = -62.0
    HAIR_GRAD_SPAN = 126.0
    # Fringe: ((tip x, tip y), (notch x, notch y)) right-to-left. See _face_hair for why
    # the tips sit where they do -- the bean eyes are a hard constraint on the dips.
    # The balance is lopsided the same way the locks are: the right temple wisp is the
    # long one (y+13) and the left is cut back (y+8), which is the sweep away from the
    # parting.
    FRINGE_TEETH = (
        ((28.0, 13.0), (23.0, -6.0)),
        ((12.0, -7.0), (8.0, -14.0)),
        ((-2.0, 3.0), (-6.0, -11.0)),
        ((-17.0, -7.0), (-21.0, -13.0)),
        ((-31.0, 8.0), (-35.0, -3.0)),
    )
    # Which tooth `ear_l` bounces, and by how much.
    FRINGE_FLICK_I = 4
    FRINGE_FLICK = 4.0
    # Where the toothed edge begins, on the right. Its other end is the last notch in
    # FRINGE_TEETH -- not a separate constant, because the two cheek strands have to
    # start exactly where this line stops. Held apart as two hand-typed pairs they
    # drifted by a unit and the join showed as a nick in the outline.
    FRINGE_START = (34.0, -4.0)
    # How far above the top of the head the fringe's arch reaches, and where its peak
    # sits left-to-right. The peak is the parting, at roughly cx+15. Move it and the
    # fringe's longest wisp and the strand-line roots have to move with it, or it stops
    # being a parting and becomes three unrelated details.
    FRINGE_ARCH = 24.0
    FRINGE_PEAK_X = 34.0
    # Interior detail, both clipped to the fringe: HAIR_L glint segments (x0,y0,x1,y1)
    # and HAIR_D strand lines (root, ctrl1, ctrl2, end), all relative to (cx, cy).
    HAIR_GLINT = (
        (-22.0, -19.0, -10.0, -24.0),
        (-3.0, -26.0, 9.0, -27.0),
        (16.0, -25.0, 26.0, -19.0),
    )
    HAIR_STRANDS = (
        ((6.0, -46.0), (-8.0, -39.0), (-25.0, -27.0), (-32.0, -15.0)),
        ((11.0, -47.0), (1.0, -41.0), (-11.0, -30.0), (-18.0, -20.0)),
        ((16.0, -46.0), (13.0, -38.0), (7.0, -27.0), (1.0, -18.0)),
        ((21.0, -42.0), (24.0, -34.0), (27.0, -20.0), (27.0, -7.0)),
    )

    @classmethod
    def _fill(cls, cy: float) -> QBrush:
        """The one hair brush. Both masses go through here so neither can drift."""
        return _hair_fill(cy + cls.HAIR_GRAD_TOP, cls.HAIR_GRAD_SPAN)

    @classmethod
    def draw(cls, p: QPainter, pose: Pose) -> None:
        body_dy = pose.breath * 1.0 + pose.slump * 3.0
        cx = 100.0 + pose.look_x * 4.0
        cy = cls.HEAD_CY + pose.look_y * 3.0 + body_dy + pose.slump * 8.0 - pose.surprise * 2.0

        # Jacket, then arms, then hair: the whole mass is in front of both her clothes
        # and her sleeves, and there is exactly one hair pass. The alternative -- mass
        # behind the jacket with extra strands in front of it -- is what produced the two
        # overlapping outlines down each shoulder. Arms specifically before the hair
        # because the locks hang past the shoulder line; see _HAIR_FALL for the whole
        # argument, which is most of why this hairstyle looks the way it does.
        cls.draw_keyboard(p)
        cls._jacket(p, body_dy)
        cls._arms(p, pose, body_dy)
        cls._hair(p, pose, cx, cy)
        cls._face(p, pose, cx, cy)
        cls._choker(p, cx, cy)
        cls._ribbon(p, pose.ear_r, cx, cy)
        if pose.zzz >= 0.0:
            cls.draw_zzz(p, pose.zzz, cx + 24.0, cy - 30.0)

    # -- hair -------------------------------------------------------------

    @classmethod
    def _hair(cls, p: QPainter, pose: Pose, cx: float, cy: float) -> None:
        """The entire hair mass, as one silhouette with one outline.

        Skull discs, the two hanging strands a side, and the ahoge all go into the same
        `merged` call. The ahoge is in here rather than drawn on top for the reason at
        the top of this file: an earlier pass had it as a separately stroked lock, which
        put a closed ink loop in the middle of the pink for the sake of one bump in the
        outline. Merged, its base is never drawn -- the crown oval swallows it -- so what
        is left is one strand standing off a smooth dome.
        """
        s = pose.tail
        shapes = [_disc(cx + x, cy + y, rx, ry) for x, y, rx, ry in cls.HAIR_CROWN]
        for x, y, w, h, rot in cls.HAIR_FALL:
            # The sway rides on the tips, not the parting: the strands are rooted up
            # near the crown, so it goes on the angle rather than on the root.
            shapes.append(_lock(cx + x + s * 1.2, cy + y, w, h, rot + s * 4.0))
        # Same sway, halved, and with the OPPOSITE sign on `rot` -- which is what makes it
        # go the same way in the picture. Rotation swings a tip anticlockwise, so on a
        # lock hanging down (+rot) the tip travels left, while on one pointing up the same
        # +rot carries it right. Matching the parameter instead of the direction is how
        # you get an ahoge that flicks against the hair every time she types. Halved
        # because it is short and rooted at the crown, so its tip already sweeps the
        # widest arc on her.
        ax, ay, aw, ah, arot = cls.HAIR_AHOGE
        shapes.append(_lock(cx + ax, cy + ay, aw, ah, arot - s * 2.0))
        merged(p, shapes, INK, cls._fill(cy), STROKE)

    @classmethod
    def _face_hair(cls, p: QPainter, pose: Pose, cx: float, cy: float) -> None:
        """Fringe plus both cheek strands: ONE fill, and ONE stroked line.

        The fringe and the strands used to be two separate merged shapes, each with its
        own closed outline, sitting on top of each other at the temples -- which is
        where the worst of the tangle was. Here they are `united` into a single fill,
        and the only stroke is the boundary that actually borders skin: up the left
        strand, along the ragged bottom of the fringe, down the right strand. It is one
        continuous polyline from one strand tip to the other, so there is nothing for it
        to cross.

        Each strand's *outer* edge is deliberately pushed outside the face ellipse, so
        it lies over the pale mass rather than over skin and needs no line at all. It
        hides a stretch of the face outline on the way past, which is what hair in
        front of a cheek is supposed to do -- an outline disappearing behind a shape
        reads as depth, unlike two outlines crossing.
        """
        flick = pose.ear_l
        # Right to left along the bottom edge: (tip x,y), (notch x,y).
        #
        # SWEPT, not scalloped. In the reference the fringe is a handful of long uneven
        # wisps running diagonally across the forehead, alternating long-short-long, with
        # the parting right of centre. Six teeth of even depth and even spacing -- the
        # last version -- read as a scalloped border sewn onto her forehead instead,
        # because nothing in it pointed anywhere. The direction comes from where the tip
        # sits between its two notches: put it close to the left-hand notch and the long
        # straight side of the wisp runs down-left, which is the sweep.
        #
        # The hard constraint is the eyes. The beans are drawn after this, so any stretch
        # of this line that passes over one is swallowed whole, and a line that stops dead
        # at a black shape and picks up again on the far side is the same mistake as a
        # hair strand skewered by a sleeve. So the long wisps only dip in the three gaps
        # the beans leave -- outside x=+-23, and the narrow channel between them -- and
        # everywhere the line crosses an eye column it stays up at y=-5 or above.
        # The outermost wisp on each side is short, and the ends of this line are where
        # the side locks take over. A first attempt ran a long wisp down to y=+15 out at
        # x=+-30, which is the same place the lock is: same fill either side of the lock's
        # own edge, so that edge became a line drawn pink-on-pink down the middle of her
        # hair -- a stray line, by the rule at the top of this file. The fringe has to
        # stop where the lock starts.
        #
        # NEEDLES, not teeth. What made the last version a paper crown was not the number
        # of points, it was their angle: a tip with its two notches 8 units away on either
        # side is an isoceles triangle, and a row of triangles is bunting. Each notch here
        # sits only 4 units to the LEFT of its tip, so the tip is acute and asymmetric --
        # one long slant coming into it from the upper right, then almost straight back up.
        # That is a slender wisp of hair pointing down-left, which is the whole sweep, and
        # it is what the reference's fringe is made of.
        #
        # Three of them carry, at the two temples and in the channel between the eyes; the
        # two over the eyes are only 5 or 6 deep, so they ripple rather than point.
        #
        # The table is FRINGE_TEETH, at the top of the class. Notes on the rows, in order:
        #   0  temple, the deepest on the right
        #   1  just clear of the top of the bean, not hovering above the eyebrow. Up at
        #      y=-10 there was a band of bare forehead between fringe and eyes and the
        #      whole thing read as a zigzag hat brim rather than as hair on her eyes.
        #   2  shallow in the MIDDLE, deep at the outer corners -- the opposite way round
        #      from the first attempt, which ran this wisp down to y=+16, level with the
        #      bottom of the beans. One long spike down the centre of a face is a widow's
        #      peak, or a bat; the parting is at the top of her head and the hair sweeps
        #      *out* from it, so the longest wisps are at the temples.
        #   3  over the left bean, shallow for the same reason as 1
        #   4  the wisp `ear_l` twitches. It used to drive a cowlick standing off the
        #      crown; the reference has no such spike -- the top of her head is a smooth
        #      dome -- so a keypress bounces the front of the fringe instead, which is
        #      both closer to the reference and harder to misread.
        edge = QPainterPath(QPointF(cx + cls.FRINGE_START[0], cy + cls.FRINGE_START[1]))
        for i, (tip, notch) in enumerate(cls.FRINGE_TEETH):
            dy = flick * cls.FRINGE_FLICK if i == cls.FRINGE_FLICK_I else 0.0
            edge.lineTo(QPointF(cx + tip[0], cy + tip[1] + dy))
            edge.quadTo(QPointF(cx + notch[0] + 3.0, cy + notch[1] + 5.0),
                        QPointF(cx + notch[0], cy + notch[1]))

        # The control points go well above `top` so the arch reaches the crown. With
        # them at `top` the arch peaked around the eyebrows, which left a pale band of
        # the mass behind showing between the arch and the top of the head -- and a
        # smooth pale arc across the forehead is an Alice band whether it is drawn
        # with a stroke or, as here, with nothing but a tone change. Pushed up, the
        # boundary lands at the crown, which is where a parting belongs: the fringe
        # *is* the top of the head, and the paler hair is what shows behind it.
        # The second control is pulled right so the peak lands right of centre: that is
        # where her parting is, and the fringe is deepest on the far side of it.
        #
        # Both ends sit at +-42, outside the head, not at +-38 on it. On the head the
        # fringe's boundary ran within a pixel of the face outline for a stretch of the
        # right temple, so the outer half of that 2.8-wide pen stuck out from under the
        # fill: a hairline of ink up the side of her head, out of nowhere, which is
        # exactly the sort of thing that reads as a stray line. Anything meant to cover
        # an outline has to cover it by more than the pen is wide.
        arch = cy - cls.HEAD_RY - cls.FRINGE_ARCH
        fringe = QPainterPath(QPointF(cx - 42.0, cy + 2.0))
        fringe.cubicTo(QPointF(cx - 44.0, arch), QPointF(cx + cls.FRINGE_PEAK_X, arch),
                       QPointF(cx + 42.0, cy - 8.0))
        fringe.connectPath(edge)
        fringe.closeSubpath()

        # The two junctions are the ends of the toothed edge, not points near them: the
        # strand strokes have to start exactly where that line stops or the join shows
        # as a nick. Both are read back off the tables for that reason.
        s = pose.tail
        last_notch = cls.FRINGE_TEETH[-1][1]
        l_join = QPointF(cx + last_notch[0], cy + last_notch[1])
        r_join = QPointF(cx + cls.FRINGE_START[0], cy + cls.FRINGE_START[1])
        l_tip = QPointF(cx - 24.0 + s * 1.6, cy + 31.0)
        r_tip = QPointF(cx + 25.0 + s * 1.6, cy + 28.0)

        # Inner edges: down the cheek, curling slightly toward the jaw. Both tips stop
        # *inside* the face ellipse, so each stroke ends on skin -- which is what a
        # tapering hair tip looks like. Run them past the jaw instead and the line has
        # to cross the face outline to get out.
        l_in = QPainterPath(l_join)
        l_in.cubicTo(QPointF(cx - 33.0, cy + 8.0), QPointF(cx - 32.0, cy + 20.0), l_tip)
        r_in = QPainterPath(r_join)
        r_in.cubicTo(QPointF(cx + 33.0, cy + 8.0), QPointF(cx + 32.0, cy + 19.0), r_tip)

        # Outer edges close each strand back up under the fringe, so the straight root
        # chord a `_lock` would leave never exists in the first place. They bow out to
        # x=+-48, well past the cheek: in the reference the locks framing her face are
        # thick ropes of hair, not wisps, and a thin one here just looked like a crease
        # down the side of her face. There is room, because the temple discs of the mass
        # reach past 50 -- the strand stays inside the silhouette the whole way, so all
        # it costs is a band of deeper pink.
        #
        # Both close *under* the fringe, at x=+-34 rather than +-38. Ending them a unit
        # past the fringe's own corner left a sliver of the closing chord sticking out
        # above it, and since the lock is filled a shade deeper than the mass that sliver
        # showed as a thin scratch across the temple. Nothing here is stroked, but a tone
        # edge in the wrong place costs exactly as much as a line in the wrong place.
        left = QPainterPath(l_in)
        left.cubicTo(QPointF(cx - 44.0, cy + 20.0), QPointF(cx - 46.0, cy - 4.0),
                     QPointF(cx - 34.0, cy - 15.0))
        left.closeSubpath()
        right = QPainterPath(r_in)
        right.cubicTo(QPointF(cx + 45.0, cy + 18.0), QPointF(cx + 46.0, cy - 2.0),
                      QPointF(cx + 34.0, cy - 15.0))
        right.closeSubpath()

        p.setPen(Qt.NoPen)
        # The SAME brush, with the same origin, as the mass behind it -- see _hair_fill.
        # Any second gradient here turns the fringe into a cap laid over her head.
        p.setBrush(cls._fill(cy))
        shape = fringe.united(left).united(right)
        p.drawPath(shape)

        # Specular band: three broken lozenges across the fringe, HAIR_L, no outline.
        # The reference has an unmissable one of these and it is most of what makes the
        # hair read as hair instead of a pink shape. Two things keep it out of trouble.
        # It is BROKEN -- a single unbroken arc across a forehead is an Alice band, which
        # this skin has already been through once. And it sits at y=-30, not on the
        # crown: up there the fill is HAIR and a HAIR_L mark on it is invisible, because
        # a white highlight on a white shape is nothing at all. At -30 the fill has
        # reached the mid pink, so there is something for it to be lighter than.
        #
        # Everything from here to the outline is clipped to the fringe. The fringe's arch
        # reaches higher than the mass behind it, so a mark placed by eye near the parting
        # can end up outside the merged silhouette's ink rim -- which is what happened on
        # the first attempt: the strand lines met at a point that stuck out of the top of
        # her head like an antenna.
        p.save()
        p.setClipPath(shape)
        p.setPen(pen(HAIR_L, 6.0))
        for x0, y0, x1, y1 in cls.HAIR_GLINT:
            p.drawLine(QPointF(cx + x0, cy + y0), QPointF(cx + x1, cy + y1))

        # Strand lines, combed out of the parting. These are the other half of what the
        # reference uses instead of tone blocks, and they are the reason the one-stroked-
        # outline rule survives contact with a detailed hairstyle: they are OPEN curves,
        # they are nested (each one's start and end are both further left than the last),
        # so no two of them can cross -- unlike the five closed, separately outlined lock
        # shapes this hair started as.
        #
        # They do NOT share an origin. Four lines from one point is a starburst, the
        # oldest failure on this character: hair has to look combed, which means roughly
        # parallel, which means the roots are spread along the parting rather than piled
        # on it. They are HAIR_D, not INK: interior hair detail is tone, and a second ink
        # weight inside the pink reads as a crack. Each stops short of the fringe's bottom
        # edge rather than meeting it, because a thin line running into a thick one makes
        # a T-junction, and a T-junction reads as a mistake.
        p.setBrush(Qt.NoBrush)
        p.setPen(pen(HAIR_D, 1.6))
        for root, c1, c2, end in cls.HAIR_STRANDS:
            strand = QPainterPath(QPointF(cx + root[0], cy + root[1]))
            strand.cubicTo(QPointF(cx + c1[0], cy + c1[1]), QPointF(cx + c2[0], cy + c2[1]),
                           QPointF(cx + end[0], cy + end[1]))
            p.drawPath(strand)
        p.restore()

        # One line, left tip -> up the cheek -> across the fringe -> down to the right
        # tip. `edge` runs right to left, so both it and the left strand go in reversed.
        line = l_in.toReversed()
        line.connectPath(edge.toReversed())
        line.connectPath(r_in)
        p.setPen(pen(INK, 2.6))
        p.setBrush(Qt.NoBrush)
        p.drawPath(line)

    # -- head -------------------------------------------------------------

    @classmethod
    def _face(cls, p: QPainter, pose: Pose, cx: float, cy: float) -> None:
        p.setPen(pen(INK, 2.8))
        p.setBrush(QBrush(SKIN))
        p.drawEllipse(QRectF(cx - cls.HEAD_RX, cy - cls.HEAD_RY,
                             cls.HEAD_RX * 2.0, cls.HEAD_RY * 2.0))
        cls._face_hair(p, pose, cx, cy)
        cls._eyes(p, pose, cx, cy)
        cls._blush(p, pose, cx, cy)
        cls._mouth(p, pose, cx, cy + 23.0)

    @classmethod
    def _eyes(cls, p: QPainter, pose: Pose, cx: float, cy: float) -> None:
        open_amt = max(0.0, min(1.0, pose.eye_open))
        for side in (-1.0, 1.0):
            ex = cx + side * 15.0 + pose.look_x * 3.0
            ey = cy + 5.0 + pose.look_y * 2.5
            if open_amt < 0.25:
                p.setBrush(Qt.NoBrush)
                p.setPen(pen(INK, 3.0))
                lid = QPainterPath(QPointF(ex - 8.5, ey + 1.0))
                lid.quadTo(QPointF(ex, ey - 7.0), QPointF(ex + 8.5, ey + 1.0))
                p.drawPath(lid)
                continue

            # Bean eyes, same language as the derp Furina skins: one solid shape, no
            # outline, no sclera, no iris. Two earlier passes proved the middle ground
            # does not exist at this size -- a flat blue-violet block with nothing
            # around it read as goggles worn over her eyes, and building it out into a
            # proper anime eye (white, gradient iris, pupil, heavy lash line) worked
            # but put four more stroked shapes on a face that already had too many
            # lines in it. A bean has one edge, and a glance moves the whole bean
            # instead of sliding a pupil around inside a socket.
            #
            # Dark violet rather than INK so she is not literally wearing Furina's
            # eyes, and the glint stays on always: blank is the joke over there, not
            # here.
            grow = 1.0 + pose.surprise * 0.28
            rx = 7.4 * grow
            ry = 8.5 * grow * open_amt
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(VIOLET.darker(135)))
            p.drawEllipse(QRectF(ex - rx, ey - ry, rx * 2.0, ry * 2.0))
            p.setBrush(QBrush(QColor(255, 255, 255, 215)))
            p.drawEllipse(QRectF(ex - rx * 0.62, ey - ry * 0.60,
                                 rx * 0.50, ry * 0.42))

    @classmethod
    def _blush(cls, p: QPainter, pose: Pose, cx: float, cy: float) -> None:
        alpha = int(80 + pose.surprise * 100)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(BLUSH_C.red(), BLUSH_C.green(), BLUSH_C.blue(), alpha)))
        for side in (-1.0, 1.0):
            p.drawEllipse(QRectF(cx + side * 26.0 - 8.5, cy + 14.0, 17.0, 9.0))

    @classmethod
    def _mouth(cls, p: QPainter, pose: Pose, mx: float, my: float) -> None:
        """Always slightly open -- she is grinning in the reference, and a closed line
        under bean eyes turns her from cheerful-dumb into blank. `mouth` opens it
        into the yawn."""
        gape = 0.26 + max(0.0, min(1.0, pose.mouth)) * 0.74
        w = 4.6 + gape * 4.2
        h = 3.0 + gape * 11.0
        grin = QPainterPath(QPointF(mx - w, my))
        grin.quadTo(QPointF(mx, my - h * 0.30), QPointF(mx + w, my))
        grin.quadTo(QPointF(mx, my + h), QPointF(mx - w, my))
        grin.closeSubpath()
        p.setPen(pen(INK, 2.2))
        p.setBrush(QBrush(LIP))
        p.drawPath(grin)
        p.save()
        p.setClipPath(grin)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(WHITE))
        p.drawRect(QRectF(mx - w, my - h * 0.4, w * 2.0, h * 0.40))
        p.restore()

    @classmethod
    def _choker(cls, p: QPainter, cx: float, cy: float) -> None:
        """Black band and brass buckle, just below the chin.

        Cheap to draw and the strongest single cue she has: it is the one piece of
        near-black in an otherwise pink-and-white character, so the eye lands on it.
        """
        y = cy + cls.HEAD_RY - 3.0
        p.setPen(pen(INK, 2.0))
        p.setBrush(QBrush(CHOKER))
        p.drawRoundedRect(QRectF(cx - 15.0, y, 30.0, 7.5), 3.0, 3.0)
        p.setBrush(_grad(cx - 5.0, y, cx + 5.0, y + 7.5, BRASS_L, BRASS))
        p.drawRoundedRect(QRectF(cx - 4.6, y + 0.8, 9.2, 6.0), 2.0, 2.0)

    @classmethod
    def _ribbon(cls, p: QPainter, flutter: float, cx: float, cy: float) -> None:
        """Pale blue ribbon at the side of the head, where the reference has it.

        The first version gave her a big bow on top instead. That bow is not in the
        reference at all, and a made-up accessory in the silhouette slot is worse
        than no accessory: it is the thing people check first.
        """
        # Moved out 5 and up 4 when the eyes grew: the bow's inner loop reaches 14 back
        # from this anchor, which at cx+33 put it on top of the eye. A bow overlapping
        # an eye does not read as depth, it reads as a bow growing out of her eye.
        p.save()
        p.translate(cx + 38.0, cy + 2.0)
        p.rotate(16.0 + flutter * 10.0)
        p.setPen(pen(INK, 2.0))
        for side in (-1.0, 1.0):
            loop = QPainterPath(QPointF(0.0, 0.0))
            loop.cubicTo(QPointF(side * 6.0, -9.0), QPointF(side * 16.0, -7.0),
                         QPointF(side * 14.0, 0.0))
            loop.cubicTo(QPointF(side * 16.0, 7.0), QPointF(side * 6.0, 6.0),
                         QPointF(0.0, 0.0))
            loop.closeSubpath()
            p.setBrush(_grad(0.0, -8.0, 0.0, 7.0, BLUE_P, BLUE))
            p.drawPath(loop)
        streamer = QPainterPath(QPointF(-2.0, 2.0))
        streamer.cubicTo(QPointF(-5.0, 12.0), QPointF(0.0, 20.0), QPointF(4.0, 24.0))
        streamer.cubicTo(QPointF(5.0, 15.0), QPointF(6.0, 9.0), QPointF(3.0, 2.0))
        streamer.closeSubpath()
        p.setBrush(_grad(0.0, 2.0, 0.0, 24.0, BLUE_P, BLUE_D))
        p.drawPath(streamer)
        p.setBrush(QBrush(BLUE))
        p.drawEllipse(QRectF(-3.4, -3.4, 6.8, 6.8))
        p.restore()

    # -- body -------------------------------------------------------------

    @classmethod
    def _jacket(cls, p: QPainter, body_dy: float) -> None:
        top = 98.0 + body_dy
        hw = cls.COAT_HALF
        sy = top + 11.0
        hem = hw * 0.78
        jacket = QPainterPath(QPointF(100.0 - hw * 0.30, top))
        jacket.quadTo(QPointF(100.0 - hw, top + 1.0), QPointF(100.0 - hw, sy))
        jacket.cubicTo(QPointF(100.0 - hw, sy + 8.0),
                       QPointF(100.0 - hem, 120.0), QPointF(100.0 - hem, 132.0))
        jacket.lineTo(QPointF(100.0 + hem, 132.0))
        jacket.cubicTo(QPointF(100.0 + hem, 120.0),
                       QPointF(100.0 + hw, sy + 8.0), QPointF(100.0 + hw, sy))
        jacket.quadTo(QPointF(100.0 + hw, top + 1.0), QPointF(100.0 + hw * 0.30, top))
        jacket.closeSubpath()
        p.setPen(pen(INK, 2.8))
        p.setBrush(_grad(100.0, top, 100.0, 132.0, WHITE, CREAM))
        p.drawPath(jacket)

        # Cape collar, pale blue, spread over both shoulders.
        p.setPen(pen(INK, 2.2))
        p.setBrush(_grad(100.0, top, 100.0, 128.0, BLUE_P, BLUE))
        for side in (-1.0, 1.0):
            cape = QPainterPath(QPointF(100.0 + side * 4.0, top + 2.0))
            cape.quadTo(QPointF(100.0 + side * hw * 0.9, top + 3.0),
                        QPointF(100.0 + side * (hw - 2.0), sy + 3.0))
            cape.cubicTo(QPointF(100.0 + side * (hw - 6.0), sy + 12.0),
                         QPointF(100.0 + side * 24.0, 124.0),
                         QPointF(100.0 + side * 13.0, 127.0))
            cape.closeSubpath()
            p.drawPath(cape)

        # Outlined, not bare fill: two unoutlined dots of brass on white read as
        # specks of dirt rather than as buttons.
        p.setPen(pen(INK, 1.4))
        p.setBrush(_grad(97.0, 0.0, 103.0, 0.0, BRASS_L, BRASS))
        for y in (118.0, 127.0):
            p.drawEllipse(QRectF(97.2, y, 5.6, 5.6))

        cls._flower(p, 82.0, 122.0)

    @classmethod
    def _flower(cls, p: QPainter, x: float, y: float) -> None:
        """The white bloom on her chest. Five petals merged into one silhouette --
        outlined separately they read as a bunch of grapes."""
        petals = []
        for i in range(5):
            a = math.radians(-90.0 + i * 72.0)
            petals.append(_disc(x + math.cos(a) * 5.2, y + math.sin(a) * 5.2, 4.2, 4.2))
        merged(p, petals, INK, QBrush(WHITE), 1.8)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(BLUE_P))
        p.drawEllipse(QRectF(x - 3.4, y - 3.4, 6.8, 6.8))
        p.setBrush(QBrush(BLUSH_C))
        p.drawEllipse(QRectF(x - 1.8, y - 1.8, 3.6, 3.6))

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
        """White jacket sleeve, blue cuff band, bare round hand.

        Three different shapes on purpose. The version this replaces was a capsule, a
        white ball and an arc, all about the same size and all crowded into the last
        14px of the arm, which stacked up into something that read as a hat sitting on
        the keyboard.

        The hand stays skin-coloured -- unlike Furina, who is in white gloves, the hand
        in skins/ref/4.webp is bare and the white there is only the sleeve cuff. But it
        is round, for the same reason Furina's is: knuckle lobes at 20px across do not
        read as fingers, they only make the outline lumpy, and lumpy reads as a mistake.
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
        p.setBrush(_grad(sx, sy, wx, wy, WHITE, CREAM))
        p.drawPath(sleeve)

        p.save()
        p.translate(wx, wy)
        p.rotate(math.degrees(ang))
        p.setPen(pen(INK, 2.0))
        p.setBrush(_grad(-3.0, 0.0, 3.0, 0.0, BLUE_P, BLUE))
        p.drawRoundedRect(QRectF(-2.6, -8.0, 6.6, 16.0), 2.6, 2.6)
        p.restore()

        # Hand last, so it overlaps the cuff and sits on the end of the arm rather than
        # beside it. No crease lines: at this size a line across the ball reads as a
        # crack, not as a knuckle.
        r = 9.5
        p.setPen(pen(INK, 2.6))
        p.setBrush(_grad(hx, hy - r, hx, hy + r, SKIN, SKIN.darker(112)))
        p.drawEllipse(QRectF(hx - r, hy - r, r * 2.0, r * 2.0))
