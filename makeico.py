"""Generate app.ico from the same drawing code, so the exe icon never drifts."""

from __future__ import annotations

import sys

from PySide6.QtGui import QGuiApplication, QImageWriter

import skins
from window import make_icon


def main() -> int:
    app = QGuiApplication(sys.argv)
    fmts = {bytes(f).decode() for f in QImageWriter.supportedImageFormats()}
    if "ico" not in fmts:
        print("no ico writer available; formats:", sorted(fmts))
        del app
        return 1
    ok = make_icon(skins.DEFAULT, 256).pixmap(256, 256).save("app.ico")
    print("app.ico written" if ok else "app.ico FAILED")
    del app
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
