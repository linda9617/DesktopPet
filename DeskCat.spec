# -*- mode: python ; coding: utf-8 -*-
# Build with build.bat (or: python -m PyInstaller --noconfirm --clean DeskCat.spec).

import os

# --exclude-module only stops Python imports. PySide6's hook still collects Qt DLLs
# that its plugins depend on -- the virtual-keyboard input plugin drags in Quick/QML/
# Network, the pdf image-format plugin drags in Qt Pdf -- so they are dropped from the
# collected files here instead. The pet paints with QPainter on a plain QWidget and
# draws its icons at runtime, so it needs no OpenGL, no image-format plugins and no
# Qt translations (menu text is hard-coded). This halves the exe (~45 MB -> ~22 MB).
DROP_FILES = (
    "opengl32sw.dll", "qt6quick", "qt6qml", "qt6pdf", "qt6network", "qt6opengl",
    "qt6virtualkeyboard", "qt6svg", "libcrypto", "libssl", "_ssl.pyd", "_hashlib.pyd",
)
DROP_DIRS = (
    "/translations/", "/imageformats/", "/iconengines/", "/generic/",
    "/platforminputcontexts/", "qdirect2d", "qminimal", "qoffscreen",
)


def keep(entry) -> bool:
    name = entry[0].lower().replace(os.sep, "/")
    return not any(d in name for d in DROP_FILES + DROP_DIRS)


a = Analysis(
    [os.path.join(SPECPATH, "main.py")],
    pathex=[SPECPATH],
    excludes=[
        "tkinter", "unittest", "pydoc", "ssl", "_ssl", "_hashlib",
        "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtNetwork", "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets", "PySide6.QtMultimedia", "PySide6.Qt3DCore",
        "PySide6.QtCharts", "PySide6.QtDataVisualization", "PySide6.QtPdf", "PySide6.QtSql",
        "PySide6.QtTest", "PySide6.QtOpenGL", "PySide6.QtSvg",
    ],
)
a.binaries = [e for e in a.binaries if keep(e)]
a.datas = [e for e in a.datas if keep(e)]

pyz = PYZ(a.pure)

# upx stays off: UPX-packed Qt DLLs are a known source of crashes and antivirus false
# positives, and a global keyboard hook already draws enough suspicion.
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="DeskCat",
    console=False,
    upx=False,
    icon=[os.path.join(SPECPATH, "app.ico")],
)
