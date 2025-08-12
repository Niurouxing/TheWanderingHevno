@echo off
setlocal

:: =================================================================
:: Hevno Engine One-Click Docker Launcher for Windows
:: =================================================================
title Hevno Engine Launcher

:check_docker
echo Checking for Docker Desktop...
docker info >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Docker Desktop is not running or not installed.
    echo Please install it from the official website and make sure it's running before you continue.
    echo https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)
echo Docker Desktop is running.

:setup_env
echo.
if exist .env (
    echo .env file found. Using existing API keys.
) else (
    echo [ACTION REQUIRED] .env file not found. Let's create it.
    echo You need a Google Gemini API Key to run this application.
    echo You can get one from Google AI Studio.
    echo.
    set /p GEMINI_KEY="Please paste your Gemini API Key here and press Enter: "
    echo GEMINI_API_KEYS="%GEMINI_KEY%"> .env
    echo .env file created successfully!
)

:launch
echo.
echo ===============================================================
echo Launching Hevno Engine via Docker...
echo.
echo The first time you run this, it will build the application
echo image. This may take several minutes. Please be patient.
echo Subsequent launches will be much faster.
echo ===============================================================
echo.

docker-compose up --build -d

if %errorlevel% neq 0 (
    echo [ERROR] Failed to start the application with Docker Compose.
    echo Please check the error messages above.
    pause
    exit /b 1
)

echo.
echo Hevno Engine is starting up in the background...
echo Please wait about 30 seconds for it to become available.

timeout /t 10 /nobreak >nul

echo.
echo Opening Hevno Engine in your web browser at http://localhost:8000
start http://localhost:8000

echo.
echo To stop the application, run the 'stop-docker.bat' script.

endlocal
pause