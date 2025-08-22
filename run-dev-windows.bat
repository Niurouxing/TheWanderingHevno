@echo off
setlocal

REM --- 脚本标题 ---
title Hevno Engine - Windows Dev Starter

REM --- 1. 环境依赖检查 ---
echo.
echo [1/5] Checking for required tools (Python, Node.js, Git)...
echo -----------------------------------------------------------------

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python not found in PATH.
    echo Please install Python 3.8+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    goto :error
)

where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found in PATH.
    echo Please install Node.js LTS from https://nodejs.org/
    echo npm (Node Package Manager) is included with Node.js.
    goto :error
)

where git >nul 2>nul
if %errorlevel% neq 0 (
    echo [WARNING] Git not found in PATH.
    echo If your Python dependencies require Git repositories, installation will fail.
    echo It is recommended to install Git from https://git-scm.com/
)

echo All required tools found.
echo.


REM --- 2. 创建并配置 Python 虚拟环境 ---
echo [2/5] Setting up Python virtual environment...
echo -----------------------------------------------------------------

if not exist .venv (
    echo Creating virtual environment in .\.venv...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create Python virtual environment.
        goto :error
    )
) else (
    echo Virtual environment .\.venv already exists.
)

echo Activating virtual environment and installing dependencies...
call .\.venv\Scripts\activate.bat
pip install --upgrade pip
pip install -e ".[dev]"

if %errorlevel% neq 0 (
    echo [ERROR] Failed to install Python dependencies.
    goto :error
)
echo Python dependencies installed successfully.
echo.


REM --- 3. 安装前端依赖 ---
echo [3/5] Installing Node.js dependencies...
echo -----------------------------------------------------------------
npm install
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install Node.js dependencies with 'npm install'.
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

echo Starting Python backend server on http://localhost:8000
start "Backend" /B uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

echo Starting Node.js frontend server on http://localhost:5173
REM 设置 VITE_API_URL 环境变量，指向本地后端服务
start "Frontend" /B cmd /c "set VITE_API_URL=http://localhost:8000&& npm run dev"

echo.
echo =================================================================
echo  All services have been started!
echo.
echo  - Backend API should be available at: http://localhost:8000
echo  - Frontend Dev Server is running at: http://localhost:5173
echo.
echo  You can close this window to stop all processes.
echo =================================================================
echo.

goto :eof

:error
echo.
echo An error occurred. Please check the messages above.
pause
exit /b 1

:eof
endlocal