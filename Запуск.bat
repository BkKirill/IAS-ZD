@echo off
chcp 65001 >nul
cd /d "%~dp0"
title ИАС-Жд
echo Запуск ИАС-Жд. Не закрывайте это окно, пока работаете с системой.
echo Чтобы остановить систему, закройте окно или нажмите Ctrl+C.
echo.
rem Через 4 секунды открываем систему в браузере
start "" /b cmd /c "timeout /t 4 /nobreak >nul & start http://localhost:5000"
py app.py
pause
