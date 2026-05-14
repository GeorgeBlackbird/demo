@echo off
setlocal

python -m pip install -r requirements.txt

if not exist "import\\app_icon.ico" (
    python -c "from PIL import Image; Image.open('import/Icon.png').save('import/app_icon.ico')"
)

python -m PyInstaller --noconfirm --onefile --windowed --name "OOO_Obuv_App" --icon "import\\app_icon.ico" main.py
if errorlevel 1 (
    echo Build FAILED. See errors above.
    pause
    exit /b 1
)

echo Build complete. EXE: dist\\OOO_Obuv_App.exe
pause

