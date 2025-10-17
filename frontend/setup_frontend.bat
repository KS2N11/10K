@echo off
echo ============================================
echo Installing Frontend Dependencies
echo ============================================
echo.

cd frontend

echo [1/2] Installing Node.js packages...
call npm install

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to install dependencies
    echo Please ensure Node.js and npm are installed
    pause
    exit /b 1
)

echo.
echo [2/2] Verifying installation...
call npm list --depth=0

echo.
echo ============================================
echo Frontend Setup Complete!
echo ============================================
echo.
echo Next steps:
echo 1. Start development server: npm run dev
echo 2. Build for production: npm run build
echo.
pause
