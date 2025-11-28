@echo off
title Init admin
call .venv\Scripts\activate
python scripts/init_admin.py
pause

