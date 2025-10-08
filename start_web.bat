@echo off
echo ========================================
echo Homalos Web服务启动
echo ========================================
call .venv\Scripts\activate
python start_web.py
pause

