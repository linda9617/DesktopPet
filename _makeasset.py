"""Key the white background out of a reference illustration into a sprite PNG.

    python _makeasset.py skins/ref/1.webp assets/furina_photo.png [--ruler]

Flood-fills near-white inwards from the border. Flood fill rather than a plain
colour threshold because the character's own hair is white too -- what protects it
is the dark line art, which walls the fill out. A threshold would punch holes in
every highlight.

`--ruler` also writes a `<out>.ruler.png` with a labelled 50px grid, for picking
crop lines by eye instead of guessing from row profiles.
"""

from __future__ import annotations

import sys
from collections import deque

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPen
from PySide6.QtWidgets import QApplication

WHITE_CUT = 238  # a pixel is background-ish if every channel is above this


def keyed(path: str) -> QImage:
    src = QImage(path)
    if src.isNull():
        raise SystemExit(f"cannot read {path}")
    im = src.convertToFormat(QImage.Format_ARGB32)
    w, h = im.width(), im.height()

    def bgish(x: int, y: int) -> bool:
        c = im.pixelColor(x, y)
        return c.red() > WHITE_CUT and c.green() > WHITE_CUT and c.blue() > WHITE_CUT

    seen = bytearray(w * h)
    q: deque[tuple[int, int]] = deque()
    for x in range(w):
        for y in (0, h - 1):
            if not seen[y * w + x] and bgish(x, y):
                seen[y * w + x] = 1
                q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if not seen[y * w + x] and bgish(x, y):
                seen[y * w + x] = 1
                q.append((x, y))
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and not seen[ny * w + nx] and bgish(nx, ny):
                seen[ny * w + nx] = 1
                q.append((nx, ny))

    out = QImage(w, h, QImage.Format_ARGB32)
    out.fill(Qt.transparent)
    for y in range(h):
        row = y * w
        for x in range(w):
            if not seen[row + x]:
                out.setPixelColor(x, y, im.pixelColor(x, y))
    return out


def ruler(im: QImage) -> QImage:
    """Checkerboard behind the sprite plus a labelled 50px grid."""
    w, h = im.width(), im.height()
    out = QImage(w, h, QImage.Format_ARGB32)
    p = QPainter(out)
    for y in range(0, h, 16):
        for x in range(0, w, 16):
            shade = 0xDD if ((x // 16) + (y // 16)) % 2 == 0 else 0xF7
            p.fillRect(x, y, 16, 16, QColor(shade, shade, shade))
    p.drawImage(0, 0, im)
    p.setPen(QPen(QColor(255, 0, 0, 170), 1))
    f = p.font()
    f.setPixelSize(11)
    p.setFont(f)
    for y in range(0, h, 50):
        p.drawLine(0, y, w, y)
        p.drawText(QPointF(2.0, y + 11.0), str(y))
    for x in range(0, w, 50):
        p.drawLine(x, 0, x, h)
        p.drawText(QPointF(x + 2.0, 11.0), str(x))
    p.end()
    return out


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]
    if len(args) != 2:
        print(__doc__)
        return 2
    src, dst = args
    im = keyed(src)
    im.save(dst)
    print(f"wrote {dst}  {im.width()}x{im.height()}")
    if "--ruler" in argv:
        r = f"{dst}.ruler.png"
        ruler(im).save(r)
        print(f"wrote {r}")
    return 0


if __name__ == "__main__":
    app = QApplication(sys.argv)
    raise SystemExit(main(sys.argv))
