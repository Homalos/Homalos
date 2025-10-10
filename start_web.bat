@echo off
echo ========================================
echo Homalos Web服务启动
echo ========================================
call .venv\Scripts\activate
set ENABLE_SSE_LOGS=true
python start_web.py
pause

