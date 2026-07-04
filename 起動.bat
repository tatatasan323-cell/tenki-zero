@echo off
chcp 932 >nul
cd /d %~dp0
if exist .venv\Scripts\python.exe (
  echo 増築部屋(venv)のPythonで起動します（Excel/PDF対応）...
  .venv\Scripts\python.exe app.py
  goto :end
)
where python >nul 2>nul
if errorlevel 1 (
  echo Python が見つかりません。https://www.python.org/downloads/ から一度だけインストールしてください。
  echo （インストール時に「Add python.exe to PATH」に必ずチェック）
  pause
  exit /b 1
)
echo tenki-zero 受付を起動します（終了はこの窓で Ctrl+C）...
python app.py
:end
pause
