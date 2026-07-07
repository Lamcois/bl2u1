@echo off
REM =====================================================
REM  Dong goi BambuLab -> Snapmaker U1 Converter thanh .exe
REM  KHONG can chay bang quyen Administrator
REM =====================================================

REM Tu nhay ve thu muc chua file bat nay
cd /d "%~dp0"

echo Thu muc lam viec: %CD%
echo.

pip install pyinstaller flask

pyinstaller --onefile --name Bambu2U1 ^
  --add-data "templates;templates" ^
  --add-data "filament_types.3mf;." ^
  --add-data "u1_template.3mf;." ^
  --add-data "u1_template_supports.3mf;." ^
  app.py

echo.
if exist "dist\Bambu2U1.exe" (
    echo Xong! File exe nam o: %CD%\dist\Bambu2U1.exe
) else (
    echo BUILD THAT BAI - xem loi phia tren.
)
pause