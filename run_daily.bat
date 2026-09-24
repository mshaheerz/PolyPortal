@echo off
echo ============================================
echo   3D Model Automation Pipeline - Daily Run
echo ============================================
cd /d "%~dp0"
set BLENDER_PYTHON="C:\Program Files\Blender Foundation\Blender 5.2\5.2\python\bin\python.exe"
set BLENDER_EXE="C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
%BLENDER_EXE% --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Blender not found!
    pause
    exit /b 1
)
echo Running pipeline...
%BLENDER_PYTHON% main.py
echo.
echo Pipeline complete. Check the output folder.
