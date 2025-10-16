@echo off
chcp 65001 >nul
echo ========================================
echo   策略管理集成测试启动脚本
echo ========================================
echo.

REM 激活虚拟环境
echo [1/4] 激活虚拟环境...
call .venv\Scripts\activate
if errorlevel 1 (
    echo ❌ 虚拟环境激活失败！请确保 .venv 目录存在
    pause
    exit /b 1
)
echo ✅ 虚拟环境已激活
echo.

REM 检查依赖
echo [2/4] 检查测试依赖...
pip show websocket-client >nul 2>&1
if errorlevel 1 (
    echo 📦 安装 websocket-client...
    pip install websocket-client
)
pip show requests >nul 2>&1
if errorlevel 1 (
    echo 📦 安装 requests...
    pip install requests
)
echo ✅ 依赖检查完成
echo.

REM 显示测试选项
echo [3/4] 请选择测试项目:
echo.
echo   1. 测试 REST API 端点
echo   2. 测试 WebSocket 实时消息
echo   3. 运行完整测试（依次执行1和2）
echo   4. 启动 Web 服务（用于前端测试）
echo   5. 查看测试文档
echo   0. 退出
echo.
set /p choice=请输入选项 (0-5): 

if "%choice%"=="1" goto test_rest_api
if "%choice%"=="2" goto test_websocket
if "%choice%"=="3" goto test_all
if "%choice%"=="4" goto start_web
if "%choice%"=="5" goto show_docs
if "%choice%"=="0" goto end
echo ❌ 无效选项，请重新运行
pause
exit /b 1

:test_rest_api
echo.
echo [4/4] 运行 REST API 测试...
echo ========================================
python tests\test_strategy_api.py
goto end_with_pause

:test_websocket
echo.
echo [4/4] 运行 WebSocket 测试...
echo ========================================
echo 💡 提示: 测试会连接到WebSocket并接收实时消息
echo 💡 按 Ctrl+C 可以中断测试
echo.
pause
python tests\test_strategy_websocket.py
goto end_with_pause

:test_all
echo.
echo [4/4] 运行完整测试...
echo ========================================
echo.
echo ▶ 第1步: REST API 测试
echo ========================================
python tests\test_strategy_api.py
echo.
echo.
echo ▶ 第2步: WebSocket 测试
echo ========================================
echo 💡 提示: 按 Ctrl+C 可以跳过WebSocket测试
echo.
timeout /t 3 >nul
python tests\test_strategy_websocket.py
goto end_with_pause

:start_web
echo.
echo [4/4] 启动 Web 服务...
echo ========================================
echo 💡 启动后访问: http://localhost:8000/docs
echo 💡 前端地址: http://localhost:5173
echo 💡 按 Ctrl+C 停止服务
echo.
python -m uvicorn src.web.main:app --reload --host 0.0.0.0 --port 8000
goto end_with_pause

:show_docs
echo.
echo [4/4] 打开测试文档...
start docs\策略管理集成测试指南.md
echo ✅ 已打开测试文档
goto end_with_pause

:end_with_pause
echo.
echo ========================================
echo ✨ 测试结束
echo ========================================
pause
exit /b 0

:end
echo.
echo 👋 再见！
exit /b 0

