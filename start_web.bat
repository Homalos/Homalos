@echo off
setlocal
echo ============================================================
echo   Homalos 量化交易系统 - Web服务启动
echo ============================================================
echo.

set "logFolder=logs"

if exist "%logFolder%" (
    echo Clearing all .log files in %logFolder%...
    del /q "%logFolder%\*.log" >nul 2>&1
    if %errorlevel% equ 0 (
        echo Operation completed successfully.
    ) else (
        echo No .log files found or error occurred.
    )
) else (
    echo Folder "%logFolder%" does not exist.
)
endlocal

echo [1/2] 启动后端服务 (端口: 8000)...
set ENABLE_SSE_LOGS=true
start "Homalos Backend" cmd /k "call .venv\Scripts\activate && python start_web_server.py"
timeout /t 3

echo [2/2] 启动前端服务 (端口: 5173)...
start "Homalos Frontend" cmd /k "cd web-ui && npm run dev"
timeout /t 2

echo.
echo ============================================================
echo   服务启动完成！
echo ============================================================
echo.
echo   后端服务: http://localhost:8000
echo   API文档:  http://localhost:8000/docs
echo   前端页面: http://localhost:5173
echo.
echo   默认管理员账户:
echo   用户名: admin
echo   密码: Admin@123456
echo.
echo   按任意键打开前端页面...
echo ============================================================
pause > nul

start http://localhost:5173

