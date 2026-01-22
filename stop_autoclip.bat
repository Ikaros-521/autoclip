@echo off
chcp 65001 >nul
title AutoClip Stopper

echo =======================================================
echo            AutoClip Service Stopper
echo =======================================================
echo.

echo [INFO] Stopping services...

:: 1. Stop by Window Title
echo [INFO] Closing service windows...
taskkill /F /FI "WINDOWTITLE eq AutoClip Backend*" /T >nul 2>nul
if %errorlevel% equ 0 echo [INFO] Backend window closed.

taskkill /F /FI "WINDOWTITLE eq AutoClip Frontend*" /T >nul 2>nul
if %errorlevel% equ 0 echo [INFO] Frontend window closed.

taskkill /F /FI "WINDOWTITLE eq AutoClip Celery*" /T >nul 2>nul
if %errorlevel% equ 0 echo [INFO] Celery window closed.

taskkill /F /FI "WINDOWTITLE eq AutoClip Redis*" /T >nul 2>nul
if %errorlevel% equ 0 echo [INFO] Redis window closed.

:: 2. Stop by Port (Backup method)
echo [INFO] Checking ports and cleaning up...

:: Stop Backend (8000)
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8000" ^| find "LISTENING"') do (
    echo [INFO] Stopping process on port 8000 (PID: %%a)...
    taskkill /F /PID %%a >nul 2>nul
)

:: Stop Frontend (3000)
for /f "tokens=5" %%a in ('netstat -aon ^| find ":3000" ^| find "LISTENING"') do (
    echo [INFO] Stopping process on port 3000 (PID: %%a)...
    taskkill /F /PID %%a >nul 2>nul
)

:: 3. Clean Redis
taskkill /F /IM redis-server.exe >nul 2>nul
if %errorlevel% equ 0 echo [INFO] Redis process cleaned.

echo.
echo [SUCCESS] All services stopped.
echo.
timeout /t 3
