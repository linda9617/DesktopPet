@echo off
setlocal
cd /d "%~dp0"

set PY=.venv\Scripts\python.exe
if not exist "%PY%" (
    echo [1/3] creating venv...
    python -m venv .venv || goto :fail
    "%PY%" -m pip install --upgrade pip || goto :fail
    "%PY%" -m pip install -r requirements.txt || goto :fail
)

echo [2/3] generating app.ico...
"%PY%" makeico.py || goto :fail

REM Every skin is drawn in code now, so there is no --add-data: nothing but the
REM icon has to be produced before PyInstaller runs.
echo [3/3] building DeskCat.exe...
"%PY%" -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name DeskCat --icon app.ico ^
    --exclude-module tkinter --exclude-module unittest --exclude-module pydoc ^
    --exclude-module PySide6.QtQml --exclude-module PySide6.QtQuick ^
    --exclude-module PySide6.QtNetwork --exclude-module PySide6.QtWebEngineCore ^
    --exclude-module PySide6.QtWebEngineWidgets --exclude-module PySide6.QtMultimedia ^
    --exclude-module PySide6.Qt3DCore --exclude-module PySide6.QtCharts ^
    --exclude-module PySide6.QtDataVisualization --exclude-module PySide6.QtPdf ^
    --exclude-module PySide6.QtSql --exclude-module PySide6.QtTest ^
    main.py || goto :fail

echo.
echo Done: dist\DeskCat.exe
dir /b /-c dist\DeskCat.exe
goto :eof

:fail
echo.
echo BUILD FAILED
exit /b 1
