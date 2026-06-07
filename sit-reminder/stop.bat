@echo off
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000.*LISTENING"') do (
    echo Stopping PID %%a...
    taskkill //PID %%a //F
)
echo 服务已停止
pause
