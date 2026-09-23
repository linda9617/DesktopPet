"""Desk Cat -- a keyboard/mouse-reactive desktop pet with switchable skins.

Run:   python main.py
Build: build.bat  ->  dist/DeskCat.exe
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

import settings
from inputwatch import InputWatcher
from pet import PetBrain
from window import PetWindow, make_icon


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Desk Cat")
    app.setQuitOnLastWindowClosed(False)

    cfg = settings.load()
    brain = PetBrain(
        idle_yawn_s=float(cfg.get("idle_yawn_s", 40.0)),
        idle_sleep_s=float(cfg.get("idle_sleep_s", 75.0)),
    )

    win = PetWindow(brain, cfg)

    watcher = InputWatcher()
    watcher.key_hit.connect(brain.on_key)
    watcher.clicked.connect(brain.on_click)
    watcher.start()
    app.aboutToQuit.connect(watcher.stop)

    tray = QSystemTrayIcon(app)
    tray.setToolTip("Desk Cat")
    tray_menu = QMenu(win)
    tray_menu.aboutToShow.connect(lambda: (tray_menu.clear(), win.populate_menu(tray_menu)))
    tray.setContextMenu(tray_menu)
    tray.activated.connect(
        lambda reason: (win.show(), win.raise_()) if reason == QSystemTrayIcon.Trigger else None
    )

    def refresh_icon() -> None:
        icon = make_icon(win.skin)
        app.setWindowIcon(icon)
        tray.setIcon(icon)

    refresh_icon()
    win.skin_changed.connect(refresh_icon)
    tray.show()

    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
