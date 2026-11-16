@echo off
title Plickers Backend Server
cd /d "%~dp0\school-response-server"
echo Starting Plickers Backend API on http://127.0.0.1:8000 ...
C:\Users\harsh\AppData\Local\Programs\Python\Python311\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --reload
pause
