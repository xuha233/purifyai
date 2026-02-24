@echo off
REM Project Team Kit Installer for Windows
REM Usage: install-project-kit.bat C:\path\to\project

if "%1"=="" (
    echo Usage: install-project-kit.bat C:\path\to\project
    exit /b 1
)

set KIT_SOURCE=%USERPROFILE%\.openclaw\templates\project-team-kit
set PROJECT_DIR=%1

echoInstalling Project Team Kit to: %PROJECT_DIR%
echo---

if not exist "%PROJECT_DIR%" (
    mkdir "%PROJECT_DIR%"
)

REM Copy all MD files to project directory
xcopy "%KIT_SOURCE%\*.md" "%PROJECT_DIR%\" /Y >nul 2>&1

echo[OK] Copied kit files to %PROJECT_DIR%
echo.
echoNext steps:
echo1. cd %PROJECT_DIR%
echo2. Edit PROJECT-IDENTITY.md with your project details
echo3. Update project type: New Project - Ongoing Project - Completed Project
echo4. Have OpenClaw read context to initialize
echo.
echoFiles installed:
dir /b "%PROJECT_DIR%\*.md"
echo.
echoReady to use! Read README.md for details.
