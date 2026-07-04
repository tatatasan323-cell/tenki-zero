@echo off
chcp 932 >nul
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 goto :nopy

echo 増築部屋を建てて、Excel・PDF対応の部品を入れます。数分かかることがあります...
python -m venv .venv
if errorlevel 1 goto :failvenv
call ".venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
call ".venv\Scripts\pip.exe" install --quiet -r requirements.txt
if errorlevel 1 goto :failpip
echo.
echo 増築完了！ 次回から 起動.bat がこの部屋を自動で使います（Excel・PDFが読めます）。
goto :end

:nopy
echo Python が見つかりません。先に https://www.python.org/downloads/ からインストールしてください。
goto :end

:failvenv
echo 増築部屋の作成に失敗しました。
goto :end

:failpip
echo 部品の導入に失敗しました（インターネット接続をご確認ください）。
goto :end

:end
pause
