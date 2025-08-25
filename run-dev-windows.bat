@echo off
setlocal enabledelayedexpansion

REM --- Installation tracking variables ---
set "PYTHON_INSTALLED=false"
set "NODEJS_INSTALLED=false"

REM --- Ensure we're in the correct directory ---
cd /d "%~dp0"
echo Current working directory: %CD%

REM --- Check for Administrator privileges ---
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [WARNING] This script is not running with Administrator privileges.
    echo Some automatic installations may fail without admin rights.
    echo.
    echo Options:
    echo 1. Right-click this file and select "Run as administrator"
    echo 2. Continue without admin rights (manual installation may be required)
    echo.
    set /p choice="Continue anyway? (y/n): "
    if /i not "%choice%"=="y" (
        echo Exiting...
        pause
        exit /b 1
    )
    echo.
) else (
    echo [INFO] Running with Administrator privileges - automatic installations enabled.
    echo.
)

REM --- 脚本标题 ---
title Hevno Engine - Windows Dev Starter

REM --- 1. 环境依赖检查 ---
echo.
echo [1/5] Checking for required tools (Python, Node.js, Git)...
echo -----------------------------------------------------------------
echo NOTE: Missing tools will be automatically installed when possible.
echo.

where python 1>nul 2>nul
if not errorlevel 1 (
    echo Python found.
) else (
    echo [INFO] Python not found in PATH. Attempting to install...
    echo Downloading and installing Python 3.11...
    set "PYTHON_INSTALLED=true"
    
    REM Create temp directory for download
    if not exist "%TEMP%\python_install" mkdir "%TEMP%\python_install"
    
    REM Download Python installer using PowerShell
    echo Downloading Python installer...
    powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.7/python-3.11.7-amd64.exe' -OutFile '%TEMP%\python_install\python.exe'}"
    
    if not exist "%TEMP%\python_install\python.exe" (
        echo [ERROR] Failed to download Python installer.
        echo Please manually install Python 3.8+ from https://www.python.org/downloads/
        goto :error
    )
    
    echo Installing Python...
    REM Install silently with pip and add to PATH
    "%TEMP%\python_install\python.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    
    REM Wait a moment for installation to complete
    timeout /t 5 /nobreak >nul
    
    if errorlevel 1 (
        echo [WARNING] Automatic installation may have failed.
        echo Trying alternative installation method...
        
        REM Try without InstallAllUsers
        "%TEMP%\python_install\python.exe" /quiet PrependPath=1 Include_test=0
        timeout /t 5 /nobreak >nul
    )
    
    REM Clean up installer
    del "%TEMP%\python_install\python.exe"
    rmdir "%TEMP%\python_install"
    
    echo Python installed successfully. Refreshing PATH...
    REM Refresh environment variables
    call :RefreshEnv
    
    REM Verify installation
    where python 1>nul 2>nul
    if not errorlevel 1 (
        echo Python installation verified successfully.
    ) else (
        echo [WARNING] Python automatic installation failed or not detected.
        echo.
        echo Manual installation required:
        echo 1. Download Python 3.8+ from: https://www.python.org/downloads/
        echo 2. Run the installer and make sure to check "Add Python to PATH"
        echo 3. Restart this script after installation
        echo.
        set /p continue="Continue without Python? This will cause errors later. (y/n): "
        if /i not "%continue%"=="y" goto :error
    )
)

where node 1>nul 2>nul
if not errorlevel 1 (
    echo Node.js found.
) else (
    echo [INFO] Node.js not found in PATH. Attempting to install...
    echo Downloading and installing Node.js LTS...
    set "NODEJS_INSTALLED=true"
    
    REM Create temp directory for download
    if not exist "%TEMP%\nodejs_install" mkdir "%TEMP%\nodejs_install"
    
    REM Download Node.js installer using PowerShell
    echo Downloading Node.js installer...
    powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://nodejs.org/dist/v22.12.0/node-v22.12.0-x64.msi' -OutFile '%TEMP%\nodejs_install\nodejs.msi'}"
    
    if not exist "%TEMP%\nodejs_install\nodejs.msi" (
        echo [ERROR] Failed to download Node.js installer.
        echo Please manually install Node.js LTS from https://nodejs.org/
        goto :error
    )
    
    echo Installing Node.js...
    REM Install silently with default options
    "%TEMP%\nodejs_install\nodejs.msi" /quiet /norestart
    
    REM Wait a moment for installation to complete
    timeout /t 3 /nobreak >nul
    
    if errorlevel 1 (
        echo [WARNING] Automatic installation may have failed.
        echo Trying alternative installation method...
        
        REM Try with msiexec
        msiexec /i "%TEMP%\nodejs_install\nodejs.msi" /quiet /norestart
        timeout /t 5 /nobreak >nul
    )
    
    REM Clean up installer
    del "%TEMP%\nodejs_install\nodejs.msi"
    rmdir "%TEMP%\nodejs_install"
    
    echo Node.js installed successfully. Refreshing PATH...
    REM Refresh environment variables
    call :RefreshEnv
    
    REM Verify installation
    where node 1>nul 2>nul
    if not errorlevel 1 (
        echo Node.js installation verified successfully.
    ) else (
        echo [WARNING] Node.js automatic installation failed or not detected.
        echo.
        echo Manual installation required:
        echo 1. Download Node.js LTS from: https://nodejs.org/
        echo 2. Run the installer and make sure to check "Add to PATH"
        echo 3. Restart this script after installation
        echo.
        set /p continue="Continue without Node.js? This may cause errors later. (y/n): "
        if /i not "%continue%"=="y" goto :error
    )
)

where git 1>nul 2>nul
if not errorlevel 1 (
    echo Git found.
) else (
    echo [WARNING] Git not found in PATH.
    echo If your Python dependencies require Git repositories, installation will fail.
    echo It is recommended to install Git from https://git-scm.com/
)

echo All required tools found.
echo.

REM --- Check if restart is required ---
if "!PYTHON_INSTALLED!"=="true" set "RESTART_REQUIRED=true"
if "!NODEJS_INSTALLED!"=="true" set "RESTART_REQUIRED=true"

if "!RESTART_REQUIRED!"=="true" (
    echo.
    echo =================================================================
    echo  RESTART REQUIRED
    echo =================================================================
    echo.
    if "!PYTHON_INSTALLED!"=="true" echo - Python was installed
    if "!NODEJS_INSTALLED!"=="true" echo - Node.js was installed
    echo.
    echo Environment variables need to be refreshed for the new installations
    echo to work properly. Please restart this script or your computer.
    echo.
    echo Press any key to exit...
    pause >nul
    exit /b 0
)

echo.
REM --- 2. 创建并配置 Python 虚拟环境 ---
echo [2/5] Setting up Python virtual environment...
echo -----------------------------------------------------------------

if not exist .venv (
    echo Creating virtual environment in .\.venv...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create Python virtual environment.
        goto :error
    )
) else (
    echo Virtual environment .\.venv already exists.
)

echo Activating virtual environment and installing dependencies...
echo Working directory: %CD%
call .\.venv\Scripts\activate.bat
echo Virtual environment activated.
echo.

echo Upgrading pip...
pip install --upgrade pip

echo Installing project dependencies...
pip install -e ".[dev]"

if errorlevel 1 (
    echo [ERROR] Failed to install Python dependencies.
    echo Working directory was: %CD%
    echo.
    echo Troubleshooting steps:
    echo 1. Check if pyproject.toml exists in current directory
    echo 2. Verify virtual environment is properly activated
    echo 3. Check internet connection
    echo.
    pause
    goto :error
)
echo Python dependencies installed successfully.
echo.


REM --- 3. 安装前端依赖 ---
echo [3/5] Installing Node.js dependencies...
echo -----------------------------------------------------------------
echo Running npm install in directory: %CD%
echo This may take several minutes, please wait...
echo.

call npm install
if errorlevel 1 (
    echo [ERROR] Failed to install Node.js dependencies with 'npm install'.
    echo.
    echo Troubleshooting steps:
    echo 1. Check your internet connection
    echo 2. Try running 'npm cache clean --force'
    echo 3. Delete node_modules folder and try again
    echo 4. Check if package.json is valid
    echo.
    pause
    goto :error
)
echo Node.js dependencies installed successfully.
echo.


REM --- 4. 模拟 entrypoint.sh 的启动前任务 ---
echo [4/5] Performing pre-start tasks...
echo -----------------------------------------------------------------

REM 复制 .env.host 到 .env
if exist .env.host (
    echo Found .env.host, copying to .env...
    copy /Y .env.host .env > nul
) else (
    echo .env.host not found, creating an empty .env file...
    type nul > .env
)

REM 如果 hevno.json 存在，则运行插件同步
if exist hevno.json (
    echo hevno.json found, running plugin synchronization...
    hevno plugins sync
) else (
    echo hevno.json not found, skipping plugin synchronization.
)
echo Pre-start tasks complete.
echo.


REM --- 5. 启动后端和前端服务 ---
echo [5/5] Starting backend and frontend services...
echo -----------------------------------------------------------------

echo Starting Python backend server on http://localhost:4399
start "Backend" /B uvicorn backend.main:app --host 127.0.0.1 --port 4399 --reload

echo Starting Node.js frontend server on http://localhost:5173
REM 设置 VITE_API_URL 环境变量，指向本地后端服务
start "Frontend" /B cmd /c "set VITE_API_URL=http://127.0.0.1:4399&& npm run dev"

echo.
echo =================================================================
echo  All services have been started!
echo.
echo  - Backend API should be available at: http://localhost:4399
echo  - Frontend Dev Server is running at: http://localhost:5173
echo.
echo  You can close this window to stop all processes.
echo =================================================================
echo.
echo Press any key to stop all services and exit...
pause >nul

goto :eof

:error
echo.
echo An error occurred. Please check the messages above.
pause
exit /b 1

:RefreshEnv
REM Refresh environment variables without restarting
for /f "tokens=2*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>nul') do set "SysPath=%%b"
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set "UserPath=%%b"
set "PATH=%UserPath%;%SysPath%"
goto :eof

:eof
endlocal