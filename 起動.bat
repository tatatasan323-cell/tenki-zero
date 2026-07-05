@echo off
chcp 932 >nul
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" goto :venv

where pythonw >nul 2>nul
if errorlevel 1 goto :console
echo tenki-zero の受付を起動します。ブラウザが開きます（受付のタブを閉じれば、システムも自動で終了します）...
start "" pythonw app.py
goto :end

:console
where python >nul 2>nul
if errorlevel 1 goto :nopy
start "" /min python app.py
goto :end

:venv
echo 増築ずみのPythonで起動します（Excel・PDF対応）...
if exist ".venv\Scripts\pythonw.exe" goto :venvw
start "" /min ".venv\Scripts\python.exe" app.py
goto :end

:venvw
start "" ".venv\Scripts\pythonw.exe" app.py
goto :end

:nopy
echo.
echo Python が見つかりませんでした。
echo https://www.python.org/downloads/ から一度だけインストールしてください。
echo インストール画面で Add python.exe to PATH に必ずチェックを。
echo.
pause

:end
