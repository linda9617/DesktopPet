"""Global keyboard / mouse watcher.

Privacy note, and the reason this file looks the way it does: a key event is
collapsed to a single character -- 'L', 'R' or 'S' -- *inside* the pynput
callback, and the key object is never stored, queued or logged. The pet only
ever learns "a left-hand key went down", which is all the animation needs.
Cursor position is polled with QCursor.pos() by the animation tick instead of
hooked, so there is no mouse-move listener at all.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from pynput import keyboard, mouse

# Left half of a QWERTY board. Anything not listed counts as right-hand.
_LEFT_CHARS = frozenset("`1234567qwertasdfgzxcvb")
_LEFT_NAMES = frozenset(
    {"tab", "caps_lock", "shift", "shift_l", "ctrl_l", "alt_l", "cmd_l", "esc", "f1",
     "f2", "f3", "f4", "f5", "f6"}
)


def _side(key) -> str:
    """Collapse a key event to 'L' / 'R' / 'S'. The key object dies here."""
    if key == keyboard.Key.space:
        return "S"
    char = getattr(key, "char", None)
    if char:
        return "L" if char.lower() in _LEFT_CHARS else "R"
    name = getattr(key, "name", "") or ""
    return "L" if name in _LEFT_NAMES else "R"


class InputWatcher(QObject):
    """Emits coarse input events on the Qt main thread."""

    key_hit = Signal(str)   # 'L' | 'R' | 'S'
    clicked = Signal(bool)  # True = left button

    def __init__(self) -> None:
        super().__init__()
        self._kb: keyboard.Listener | None = None
        self._ms: mouse.Listener | None = None

    def start(self) -> None:
        self._kb = keyboard.Listener(on_press=self._on_press)
        self._kb.daemon = True
        self._kb.start()

        self._ms = mouse.Listener(on_click=self._on_click)
        self._ms.daemon = True
        self._ms.start()

    def stop(self) -> None:
        for listener in (self._kb, self._ms):
            if listener is not None:
                listener.stop()
        self._kb = self._ms = None

    # -- callbacks run on the listener threads; signals hop to the GUI thread --

    def _on_press(self, key) -> None:
        try:
            self.key_hit.emit(_side(key))
        except Exception:
            pass

    def _on_click(self, x, y, button, pressed) -> None:
        if not pressed:
            return
        try:
            self.clicked.emit(button == mouse.Button.left)
        except Exception:
            pass
