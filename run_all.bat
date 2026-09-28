@echo off
REM WP-MORPH journal reproducibility package - Windows command-prompt launcher.
REM
REM Usage:
REM   run_all.bat
REM
REM The script does not hide errors: it returns the exit code of run_all.py.

setlocal
cd /d "%~dp0"

echo Package root : %CD%

where conda >nul 2>nul
if %ERRORLEVEL%==0 (
    conda env list | findstr /C:"wp-morph-repro" >nul 2>nul
    if %ERRORLEVEL%==0 (
        echo Activating conda environment "wp-morph-repro" ...
        conda run --no-capture-output -n wp-morph-repro python run_all.py
        exit /b %ERRORLEVEL%
    )
)

echo No conda environment named "wp-morph-repro" found; using the active interpreter.
python run_all.py
exit /b %ERRORLEVEL%
