@echo off
echo ====================================
echo    AuthVision Setup Script
echo ====================================
echo.

echo Checking Node.js installation...
node --version
if errorlevel 1 (
    echo ERROR: Node.js is not installed!
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)

echo Checking npm...
npm --version
if errorlevel 1 (
    echo ERROR: npm is not found!
    pause
    exit /b 1
)

echo.
echo Installing dependencies...
npm install

echo.
echo ====================================
echo    Setup Complete!
echo ====================================
echo.
echo To run the project, use:
echo   npm run dev
echo.
pause