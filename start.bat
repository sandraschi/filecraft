@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\filecraft-cli.exe" (
    ".venv\Scripts\filecraft-cli.exe" %*
) else (
    uv run filecraft-cli %*
)
