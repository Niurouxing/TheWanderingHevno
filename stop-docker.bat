@echo off
setlocal

:: =================================================================
:: Hevno Engine One-Click Docker Stopper for Windows
:: =================================================================
title Hevno Engine Stopper

echo Stopping Hevno Engine...
docker-compose down

echo.
echo Application has been stopped.
pause