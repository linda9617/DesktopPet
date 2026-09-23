"""Frameless always-on-top pet window, draggable, with a tray + context menu."""

from __future__ import annotations

from PySide6.QtCore import QElapsedTimer, QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QActionGroup, QCursor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QWidget

import settings
import skins
from pet import PetBrain
from pose import Pose

FPS = 30

# How long after a double-click a third click still counts as part of a triple.
# Qt has no triple-click event, so the corner-snap has to wait this long before it
# commits: snapping straight away moves the window out from under the cursor, and the
# third click then lands on the desktop instead of on the pet.
TRIPLE_MS = 280


def make_icon(skin: type[skins.Skin], px: int = 64) -> QIcon:
    """Crop the skin's head box into a square icon."""
    pm = QPixmap(px, px)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    x, y, size = skin.ICON_CROP
    p.scale(px / size, px / size)
    p.translate(-(x + skin.MARGIN), -(y + skin.MARGIN))
    skin.render(p, Pose())
    p.end()
    return QIcon(pm)


class PetWindow(QWidget):
    skin_changed = Signal()

    def __init__(self, brain: PetBrain, cfg: dict) -> None:
        super().__init__(None)
        self._brain = brain
        self._cfg = cfg
        self._skin = skins.get(cfg.get("skin"))
        self._drag_from: QPoint | None = None

        self.setWindowTitle("Desk Cat")
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._apply_flags()
        self.setCursor(Qt.OpenHandCursor)
        self.setToolTip("拖动移动 · 双击回到右下角 · 三击隐藏 · 右键菜单")

        self._resize_to_skin()
        self._restore_position()

        self._snap_timer = QTimer(self)
        self._snap_timer.setSingleShot(True)
        self._snap_timer.timeout.connect(self.reset_position)

        self._clock = QElapsedTimer()
        self._clock.start()
        self._last_ms = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(int(1000 / FPS))

    @property
    def skin(self) -> type[skins.Skin]:
        return self._skin

    # ---- window plumbing --------------------------------------------------

    def _apply_flags(self) -> None:
        flags = Qt.FramelessWindowHint | Qt.Tool
        if self._cfg.get("always_on_top", True):
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def _resize_to_skin(self) -> None:
        scale = max(0.5, min(2.5, float(self._cfg.get("scale") or 1.0)))
        self._cfg["scale"] = scale
        cw, ch = self._skin.canvas()
        self.setFixedSize(int(cw * scale), int(ch * scale))

    def _apply_scale(self, scale: float) -> None:
        self._cfg["scale"] = max(0.5, min(2.5, scale))
        self._resize_to_skin()
        self._keep_on_screen()
        self._store_geometry()

    def _apply_skin(self, key: str) -> None:
        if key == self._skin.KEY:
            return
        self._skin = skins.get(key)
        self._cfg["skin"] = self._skin.KEY
        self._resize_to_skin()
        self._keep_on_screen()
        self._store_geometry()
        self.update()
        self.skin_changed.emit()

    def _restore_position(self) -> None:
        x, y = self._cfg.get("pos_x"), self._cfg.get("pos_y")
        if x is None or y is None or not self._on_a_screen(int(x), int(y)):
            self.reset_position()
            return
        self.move(int(x), int(y))

    def _on_a_screen(self, x: int, y: int) -> bool:
        return any(
            s.availableGeometry().contains(QPoint(x + 20, y + 20)) for s in QApplication.screens()
        )

    def _keep_on_screen(self) -> None:
        """A bigger skin or scale can push the pet off the desktop edge."""
        screen = QApplication.screenAt(self.geometry().center()) or QApplication.primaryScreen()
        area = screen.availableGeometry()
        x = min(max(self.x(), area.left()), max(area.left(), area.right() - self.width()))
        y = min(max(self.y(), area.top()), max(area.top(), area.bottom() - self.height()))
        self.move(x, y)

    def reset_position(self) -> None:
        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        area = screen.availableGeometry()
        self.move(area.right() - self.width() - 16, area.bottom() - self.height() - 8)
        self._store_geometry()

    def _store_geometry(self) -> None:
        self._cfg["pos_x"] = self.x()
        self._cfg["pos_y"] = self.y()
        settings.save(self._cfg)

    # ---- animation --------------------------------------------------------

    def _tick(self) -> None:
        now = self._clock.elapsed()
        dt = max(0.001, min(0.25, (now - self._last_ms) / 1000.0))
        self._last_ms = now

        cursor = QCursor.pos()
        center = self.geometry().center()
        self._brain.update(dt, (cursor.x(), cursor.y()), (center.x(), center.y()))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        cw, _ = self._skin.canvas()
        k = self.width() / cw
        p.scale(k, k)
        self._skin.render(p, self._brain.pose)
        p.end()

    # ---- interaction ------------------------------------------------------

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.LeftButton:
            return
        if self._snap_timer.isActive():
            # Third click of a triple: drop the pending corner-snap and hide instead.
            # Any press this soon after a double-click is a triple by definition, so
            # this also rules out starting a drag here.
            self._snap_timer.stop()
            self._drag_from = None
            self.setCursor(Qt.OpenHandCursor)
            self.hide_to_tray()
            event.accept()
            return
        self._drag_from = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        self.setCursor(Qt.ClosedHandCursor)
        event.accept()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_from is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_from)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if self._drag_from is not None:
            self._drag_from = None
            self.setCursor(Qt.OpenHandCursor)
            self._store_geometry()
            event.accept()

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.LeftButton:
            return
        # Qt delivers press/release before the double-click, so a drag has already
        # started and ended by now. Clear it explicitly anyway: a window hidden with
        # the grab cursor still set comes back holding a closed hand.
        self._drag_from = None
        self.setCursor(Qt.OpenHandCursor)
        self._snap_timer.start(TRIPLE_MS)
        event.accept()

    def hide_to_tray(self) -> None:
        self.hide()

    def contextMenuEvent(self, event) -> None:  # noqa: N802
        self.build_menu().exec(event.globalPos())

    def build_menu(self) -> QMenu:
        menu = QMenu(self)
        self.populate_menu(menu)
        return menu

    def populate_menu(self, menu: QMenu) -> None:
        """Fill a menu in place, so the tray menu can rebuild on every open and
        show current check marks instead of the state at startup."""
        skin_menu = menu.addMenu("皮肤")
        skin_group = QActionGroup(skin_menu)
        skin_group.setExclusive(True)
        for skin in skins.SKINS:
            act = QAction(skin.NAME, skin_menu, checkable=True)
            act.setChecked(skin.KEY == self._skin.KEY)
            act.triggered.connect(lambda _=False, k=skin.KEY: self._apply_skin(k))
            skin_group.addAction(act)
            skin_menu.addAction(act)

        size_menu = menu.addMenu("大小")
        size_group = QActionGroup(size_menu)
        size_group.setExclusive(True)
        current = round(float(self._cfg.get("scale", 1.0)), 2)
        for label, value in (("75%", 0.75), ("100%", 1.0), ("125%", 1.25), ("150%", 1.5), ("200%", 2.0)):
            act = QAction(label, size_menu, checkable=True)
            act.setChecked(abs(current - value) < 0.01)
            act.triggered.connect(lambda _=False, v=value: self._apply_scale(v))
            size_group.addAction(act)
            size_menu.addAction(act)

        top = QAction("总在最前", menu, checkable=True)
        top.setChecked(bool(self._cfg.get("always_on_top", True)))
        top.triggered.connect(self._toggle_on_top)
        menu.addAction(top)

        menu.addAction("回到右下角（双击也可以）", self.reset_position)
        menu.addAction("隐藏（三击也可以）", self.hide_to_tray)
        menu.addSeparator()
        menu.addAction("退出", QApplication.instance().quit)

    def _toggle_on_top(self, checked: bool) -> None:
        self._cfg["always_on_top"] = checked
        was_visible = self.isVisible()
        self._apply_flags()
        if was_visible:
            self.show()
        settings.save(self._cfg)
