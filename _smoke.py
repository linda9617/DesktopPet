"""Dev helper: start the real app, exercise the brain, switch skins, grab, quit."""

from __future__ import annotations

import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

import settings
import skins
from inputwatch import InputWatcher
from pet import PetBrain
from window import PetWindow, make_icon


def main() -> int:
    app = QApplication(sys.argv)
    cfg = settings.load()
    brain = PetBrain()
    win = PetWindow(brain, cfg)

    watcher = InputWatcher()
    watcher.key_hit.connect(brain.on_key)
    watcher.clicked.connect(brain.on_click)
    watcher.start()
    win.show()

    at = 0

    def step(ms: int, fn) -> None:
        QTimer.singleShot(ms, fn)

    for skin in skins.SKINS:
        base = at
        step(base, lambda k=skin.KEY: win._apply_skin(k))
        # a typing burst through the same path the real hooks use
        for i, side in enumerate("LRLSRLRL"):
            step(base + 60 + i * 70, lambda s=side: brain.on_key(s))
        step(base + 700, lambda: brain.on_click(True))
        step(base + 760, lambda k=skin.KEY: _grab(win, k))
        step(base + 800, lambda s=skin: make_icon(s, 64))
        at = base + 900

    step(at + 200, lambda: (watcher.stop(), app.quit()))
    return app.exec()


def _grab(win: PetWindow, key: str) -> None:
    pm = win.grab()
    out = f"_live_{key}.png"
    pm.save(out)
    print(f"{out}  {pm.width()}x{pm.height()}  skin={win.skin.KEY}  "
          f"paw={win._brain.pose.paw_l:.2f}/{win._brain.pose.paw_r:.2f}  "
          f"eye={win._brain.pose.eye_open:.2f}")


if __name__ == "__main__":
    raise SystemExit(main())
