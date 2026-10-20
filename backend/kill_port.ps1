$conn = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($conn) {
    $owningPid = $conn.OwningProcess
    Stop-Process -Id $owningPid -Force -ErrorAction SilentlyContinue
    Write-Host "Killed PID $owningPid"
} else {
    Write-Host "No process on port 8000"
}
