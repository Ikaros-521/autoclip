@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

set "PROJECT_ROOT=%cd%"
set HF_ENDPOINT=https://hf-mirror.com
set HF_HOME=%PROJECT_ROOT%\hf_download
set MODELSCOPE_CACHE=%PROJECT_ROOT%\hf_download
set "TOOLS_DIR=%PROJECT_ROOT%\tools"
set "REDIS_DIR=%TOOLS_DIR%\redis"
set "VENV_DIR=%PROJECT_ROOT%\venv"
set "BACKEND_PORT=8000"
set "FRONTEND_PORT=3000"

title AutoClip Launcher
echo =======================================================
echo            AutoClip Windows Launcher
echo =======================================================
echo.

:: =======================================================
:: Configuration
:: =======================================================
:: Launch Mode: normal (default) or dev
:: normal: Uses compiled frontend, no Node.js required
:: dev: Uses Node.js/Vite for frontend hot-reloading
set "LAUNCH_MODE=dev"

:: Override with command line argument if provided
if "%~1"=="dev" set "LAUNCH_MODE=dev"
if "%~1"=="normal" set "LAUNCH_MODE=normal"

if "%LAUNCH_MODE%"=="dev" (
    set "DEV_MODE=1"
    echo [INFO] Starting in DEVELOPMENT Mode...
) else (
    set "DEV_MODE=0"
    echo [INFO] Starting in NORMAL Mode...
)
echo.

:: 1. Check Environment
echo [INFO] Checking environment...

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.10+ and add to PATH.
    pause
    exit /b 1
)

if "%DEV_MODE%"=="1" (
    where node >nul 2>nul
    if !errorlevel! neq 0 (
        echo [ERROR] Node.js not found. Development mode requires Node.js.
        echo [TIP] Please install Node.js or use Normal Mode.
        pause
        exit /b 1
    )
)

:: 2. Setup Python Virtual Environment
echo [INFO] Checking Python virtual environment...

set "NEED_INSTALL=0"

if not exist "%VENV_DIR%" (
    echo [INFO] Virtual environment not found, creating...
    python -m venv "%VENV_DIR%"
    set "NEED_INSTALL=1"
) else (
    :: Check if venv is valid
    "%VENV_DIR%\Scripts\python.exe" --version >nul 2>nul
    if !errorlevel! neq 0 (
        echo [WARNING] Virtual environment is broken, recreating...
        rmdir /s /q "%VENV_DIR%"
        python -m venv "%VENV_DIR%"
        set "NEED_INSTALL=1"
    ) else (
        echo [INFO] Virtual environment is valid.
    )
)

:: Activate venv
call "%VENV_DIR%\Scripts\activate.bat"

:: Check for critical dependencies
python -c "import uvicorn; import pysrt" >nul 2>nul
if %errorlevel% neq 0 (
    echo [INFO] Critical dependencies missing. Marking for installation.
    set "NEED_INSTALL=1"
)

:: Install dependencies
if "!NEED_INSTALL!"=="1" (
    echo [INFO] Installing Python dependencies...
    python -m pip install --upgrade pip
    
    echo [INFO] Installing requirements from requirements.txt...
    pip install -r requirements.txt
    if !errorlevel! neq 0 (
        echo [WARNING] Standard installation failed. Retrying with Tsinghua mirror...
        pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
        if !errorlevel! neq 0 (
            echo [ERROR] Failed to install dependencies.
            pause
            exit /b 1
        )
    )
)

:: 3. Environment Variables
if not exist ".env" (
    echo [INFO] Creating default .env file
    copy env.example .env >nul
)

:: Set PYTHONPATH
set "PYTHONPATH=%PROJECT_ROOT%"

:: Set FFmpeg PATH
if exist "%TOOLS_DIR%\ffmpeg\bin" (
    echo [INFO] Local FFmpeg detected, adding to PATH...
    set "PATH=%TOOLS_DIR%\ffmpeg\bin;%PATH%"
)

:: Check bcut-asr and FFmpeg
@REM echo [INFO] Checking bcut-asr and FFmpeg...
@REM python scripts/install_bcut_asr.py
@REM if %errorlevel% neq 0 (
@REM     echo [ERROR] Failed to install bcut-asr or dependencies.
@REM     echo [TIP] Please check your network connection and try again.
@REM     pause
@REM     exit /b 1
@REM )


:: 4. Start Redis
echo [INFO] Starting Redis...
set "REDIS_EXE=%REDIS_DIR%\redis-server.exe"

if exist "%REDIS_EXE%" (
    start "AutoClip Redis" /MIN "%REDIS_EXE%"
) else (
    where redis-server >nul 2>nul
    if !errorlevel! equ 0 (
        start "AutoClip Redis" /MIN redis-server
    ) else (
        echo [WARNING] Redis service not found.
        echo [TIP] Recommended: Download Redis for Windows and place it in: tools\redis\redis-server.exe
        echo [TIP] Ignoring if you have already started Redis manually.
        timeout /t 3 >nul
    )
)

:: 5. Initialize Database
if not exist "data" mkdir "data"
echo [INFO] Checking database...
python -c "import sys; sys.path.insert(0, '.'); from backend.core.database import engine, Base; Base.metadata.create_all(bind=engine); print('Database checked.')" >nul 2>nul

:: 6. Start Celery Worker
echo [INFO] Starting Celery Worker...
start "AutoClip Celery" cmd /k "title AutoClip Celery && call venv\Scripts\activate.bat && celery -A backend.core.celery_app worker --loglevel=info --pool=solo -Q processing,video,notification,upload,celery"

:: 7. Start Backend API
echo [INFO] Starting Backend Service...
start "AutoClip Backend" cmd /k "title AutoClip Backend && call venv\Scripts\activate.bat && python -m uvicorn backend.main:app --host 0.0.0.0 --port %BACKEND_PORT% --reload"


:: 8. Start Frontend (Conditional)
if "%DEV_MODE%"=="1" (
    echo [INFO] Starting Frontend Dev Server...
    cd frontend
    if not exist "node_modules\.bin\vite.cmd" (
        echo [INFO] Installing frontend dependencies...
        call npm install
        if !errorlevel! neq 0 (
            echo [WARNING] npm install failed. Retrying with npmmirror...
            call npm install --registry=https://registry.npmmirror.com
        )
    )
    start "AutoClip Frontend" cmd /k "title AutoClip Frontend && npm run dev -- --host 0.0.0.0 --port %FRONTEND_PORT%"
    cd ..
) else (
    echo [INFO] Frontend is served by Backend service.
)


:: 9. Wait and Open Browser
echo [INFO] System is starting, waiting for services...
timeout /t 8 >nul

echo [SUCCESS] Opening browser...
:: wait 3 seconds for backend to start
timeout /t 3 >nul
if "%DEV_MODE%"=="1" (
    start http://localhost:%FRONTEND_PORT%
) else (
    start http://localhost:%BACKEND_PORT%
)

echo.
echo =======================================================
echo            AutoClip Started Successfully!
echo =======================================================
echo [INFO]
if "%DEV_MODE%"=="1" (
    echo 1. Frontend: http://localhost:%FRONTEND_PORT%
    echo 2. Backend API: http://localhost:%BACKEND_PORT%/docs
) else (
    echo 1. App URL: http://localhost:%BACKEND_PORT%
    echo 2. API Docs: http://localhost:%BACKEND_PORT%/docs
)
echo.
echo [TIP] Do not close the opened console windows.
echo [TIP] To stop the application, close all console windows.
pause
