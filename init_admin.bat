@echo off
call .venv\Scripts\activate
python -m src.web.scripts.init_admin
pause

