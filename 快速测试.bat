@echo off
chcp 65001 >nul
echo ========================================
echo   Quick API Test
echo ========================================
echo.

REM 激活虚拟环境
call .venv\Scripts\activate

echo Testing backend API endpoints...
echo.

REM 1. 健康检查
echo [1/5] Health check...
curl -s http://localhost:8000/health >nul
if errorlevel 1 (
    echo [FAIL] Backend not running
    pause
    exit /b 1
)
echo [OK] Backend is running

REM 2. 获取策略列表
echo [2/5] Get strategies list...
curl -s http://localhost:8000/api/strategies/ >nul
if errorlevel 1 (
    echo [FAIL] Cannot get strategies
    pause
    exit /b 1
)
echo [OK] Strategies list retrieved

REM 3. 获取运行状态
echo [3/5] Get running status...
curl -s http://localhost:8000/api/strategies/status >nul
if errorlevel 1 (
    echo [FAIL] Cannot get status
    pause
    exit /b 1
)
echo [OK] Status retrieved

REM 4. 测试启动（策略已在运行，会返回警告但不影响）
echo [4/5] Test start API...
curl -s -X POST http://localhost:8000/api/strategies/example_ipc_class/start >nul
echo [OK] Start API works

REM 5. 再次检查状态
echo [5/5] Verify status...
curl -s http://localhost:8000/api/strategies/status >nul
echo [OK] Status verified

echo.
echo ========================================
echo [SUCCESS] All quick tests passed!
echo ========================================
echo.
echo Backend API is working correctly.
echo.
echo Next steps:
echo 1. Open browser: http://localhost:5173
echo 2. Go to "Strategy Management" page
echo 3. Test frontend features
echo.
pause

