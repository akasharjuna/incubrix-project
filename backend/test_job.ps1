$body = @{
    script = "A beautiful sunset over the ocean with golden waves crashing on the beach. People enjoy summer vacation on tropical islands."
    aspect_ratios = @("16:9")
    captions = @{
        enabled = $false
        burn_in = $false
    }
} | ConvertTo-Json -Depth 5

Write-Host "Submitting job..."
$resp = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/broll/jobs" -ContentType "application/json" -Body $body
Write-Host "Job created: $($resp.job_id)"
Write-Host "Status: $($resp.status)"

# Poll until complete
$jobId = $resp.job_id
for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 5
    $status = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/broll/jobs/$jobId"
    $pct = $status.progress.percent
    $stage = $status.progress.stage
    $st = $status.status
    Write-Host "[$i] $st | $stage | $pct%"
    if ($st -eq "completed" -or $st -eq "failed") {
        $status | ConvertTo-Json -Depth 10
        break
    }
}
