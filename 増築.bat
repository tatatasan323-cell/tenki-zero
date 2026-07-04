@echo off
chcp 932 >nul
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python が見つかりません。先に https://www.python.org/downloads/ からインストールしてください。
  pause
  exit /b 1
)
echo 増築部屋(venv)を建てて、借り物(Excel/PDF対応の部品)を入れます。数分かかることがあります...
python -m venv .venv
if errorlevel 1 ( echo venvの作成に失敗しました & pause & exit /b 1 )
.venv\Scripts\python.exe -m pip install --quiet --upgrade pip
.venv\Scripts\pip.exe install --quiet -r requirements.txt
if errorlevel 1 ( echo 借り物の導入に失敗しました（ネット接続を確認してください） & pause & exit /b 1 )
echo.
echo 増築完了！ 次回から「起動.bat」がこの部屋を自動で使います（Excel/PDFが読めるようになりました）。
pause
