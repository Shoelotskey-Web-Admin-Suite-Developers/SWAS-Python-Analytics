@echo off
REM Daily Analytics Pipeline Runner
REM This batch file runs the daily analytics pipeline using the Python virtual environment

echo Starting Daily Analytics Pipeline at %date% %time%

REM Change to the scripts directory
cd /d "%~dp0"

REM Activate the Python virtual environment and run the pipeline
call .venv311\Scripts\activate.bat && python run_daily_analytics.py

REM Log the completion
echo Daily Analytics Pipeline completed at %date% %time%

pause
