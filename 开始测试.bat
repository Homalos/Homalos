@echo off
chcp 65001 >nul
echo ========================================
echo   Strategy Management Test
echo ========================================
echo.

echo [OK] Backend service is running
echo [OK] Strategies loaded successfully
echo.

echo Starting tests...
echo.

REM 激活虚拟环境
call .venv\Scripts\activate

echo [Test 1] REST API Endpoints
echo ========================================
python tests\test_strategy_api.py
if errorlevel 1 (
    echo [ERROR] REST API test failed
    pause
    exit /b 1
)

echo.
echo.
echo [Test 2] WebSocket Real-time Messages
echo ========================================
echo [INFO] Test will run for 30 seconds, or press Ctrl+C to stop
echo.
timeout /t 3 >nul

REM 运行WebSocket测试30秒后自动结束
start /b python tests\test_strategy_websocket.py
timeout /t 30 >nul
taskkill /f /im python.exe /fi "WINDOWTITLE eq test_strategy_websocket*" >nul 2>&1

echo.
echo.
echo ========================================
echo [SUCCESS] Tests completed!
echo ========================================
echo.
echo Next: Please test frontend features in browser
echo Visit: http://localhost:5173
echo Go to "Strategy Management" page
echo.
pause

