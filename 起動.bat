@echo off
chcp 932 >nul
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" goto :venv

where python >nul 2>nul
if errorlevel 1 goto :nopy
echo tenki-zero の受付を起動します（終了はこの黒い窓で Ctrl+C）...
python app.py
goto :end

:venv
echo 増築ずみのPythonで起動します（Excel・PDF対応）...
call ".venv\Scripts\python.exe" app.py
goto :end

:nopy
echo.
echo Python が見つかりませんでした。
echo https://www.python.org/downloads/ から一度だけインストールしてください。
echo インストール画面で Add python.exe to PATH に必ずチェックを。
echo.

:end
pause
