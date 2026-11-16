@echo off
title Plickers Live - Teacher Portal
cd /d "%~dp0\teacher-ui"
echo Starting Plickers Teacher UI on http://localhost:5173 ...
npm run dev
pause
