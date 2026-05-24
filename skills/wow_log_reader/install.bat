@echo off
setlocal
set "DEST=%AppData%\ShipBit\WingmanAI\custom_skills\wow_log_reader"
echo Installing WoW Log Reader to %DEST%...
robocopy "%~dp0." "%DEST%" /E /IS /IT /XF install.bat TESTER_README.txt
if %errorlevel% leq 7 (
    echo.
    echo Install complete!
) else (
    echo.
    echo ERROR: Install failed with code %errorlevel%
)
pause
