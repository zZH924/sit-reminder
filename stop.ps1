$conn = netstat -ano | Select-String ":8000"
if ($conn) {
    $parts = $conn -split '\s+'
    $pid = $parts[$parts.Count - 1]
    Write-Host "正在停止端口 8000 上的服务，进程 PID: $pid"
    Stop-Process -Id $pid -Force
    Write-Host "服务已停止。"
} else {
    Write-Host "端口 8000 上没有正在运行的服务。"
}
Read-Host "按 Enter 退出"
