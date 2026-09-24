@echo off
:: ============================================================
::  Daily 3D Model Generator - Task Scheduler Setup
::  RIGHT-CLICK this file and choose "Run as administrator"
:: ============================================================

echo.
echo ============================================================
echo   Setting up Daily 3D Model Generator Task
echo ============================================================
echo.

set BATCH="C:\Users\Sunu\Documents\home\zaigopc\Desktop\personal\automate\run_daily.bat"
set TASKNAME=Daily3DModelGenerator
set RUNTIME=09:00

:: Delete old task if it exists
schtasks /delete /tn "%TASKNAME%" /f >nul 2>&1

:: Create the daily task
schtasks /create ^
  /tn "%TASKNAME%" ^
  /tr "\"%BATCH%\"" ^
  /sc daily ^
  /st %RUNTIME% ^
  /rl highest ^
  /f

if %errorlevel% equ 0 (
    echo.
    echo ============================================================
    echo   SUCCESS! Task registered.
    echo   Name  : %TASKNAME%
    echo   Runs  : Every day at %RUNTIME%
    echo   Script: %SCRIPT%
    echo ============================================================
    echo.
    echo To change the time, edit RUNTIME in this file and re-run.
    echo To run it RIGHT NOW for testing:
    echo   schtasks /run /tn "%TASKNAME%"
) else (
    echo.
    echo ERROR: Could not create task. Make sure you ran as Administrator!
)

echo.
pause
