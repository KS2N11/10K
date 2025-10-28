$r = Invoke-RestMethod -Uri 'http://localhost:8000/api/scheduler/trigger' -Method Post
$id = $r.run_id
Write-Output "RUN_ID:$id"
for ($i=0; $i -lt 40; $i++) {
    $s = Invoke-RestMethod -Uri "http://localhost:8000/api/scheduler/runs/$id" -Method Get
    if ($s.status -in @('completed','failed')) {
        $s | ConvertTo-Json -Depth 12
        break
    } else {
        Write-Output "Status: $($s.status) - sleeping"
        Start-Sleep -Seconds 3
    }
}
