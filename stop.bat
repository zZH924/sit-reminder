@echo off
netstat -ano | find ":8000" > "%TEMP%\port8000.tmp"
set PID=
for /f "tokens=5" %%a in (%TEMP%\port8000.tmp) do set PID=%%a
del "%TEMP%\port8000.tmp" 2>nul
if defined PID (
    echo Stopping process on port 8000, PID: %PID%
    taskkill /PID %PID% /F
    echo Server stopped.
) else (
    echo No process found on port 8000.
)
pause
