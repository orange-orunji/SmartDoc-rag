# rerun.ps1 -- One-key retest loop: restart service -> wait ready -> clear cache -> (retry N) -> run eval
# Usage (run from project root or anywhere):
#   .\scripts\rerun.ps1            # full eval (all 15)
#   .\scripts\rerun.ps1 7,8,9      # only re-run questions 7,8,9
# If blocked by execution policy:
#   powershell -ExecutionPolicy Bypass -File .\scripts\rerun.ps1 7,8,9
param([int[]]$Retry = @(), [switch]$SkipEval)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $root "main.py"))) { $root = "D:\phython\RAG_Personal" }
$py = Join-Path $root ".venv\Scripts\python.exe"
$port = 8010

Write-Host "===== [1/5] Stop old service on port $port ====="
$p = (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1).OwningProcess
if ($p) {
    taskkill /PID $p /F | Out-Null
    Write-Host "Stopped PID=$p"
    Start-Sleep -Seconds 2
} else {
    Write-Host "No old service found"
}

Write-Host "===== [2/5] Start service in a NEW WINDOW (watch its log there) ====="
$cmd = "& '$py' -m uvicorn main:app --host 127.0.0.1 --port $port"
Start-Process powershell -ArgumentList "-NoProfile", "-NoExit", "-Command", $cmd -WorkingDirectory $root | Out-Null

Write-Host "===== [3/5] Wait for ready (poll /health, up to 120s) ====="
$ready = $false
for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 2
    try {
        $r = Invoke-WebRequest "http://127.0.0.1:$port/health" -TimeoutSec 2 -UseBasicParsing
        if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch {}
}
if (-not $ready) {
    Write-Host "ERROR: service not ready in 120s. Check the service window for errors."
    exit 1
}
Write-Host "Service ready."

Write-Host "===== [4/5] Clear cache ====="
& $py (Join-Path $root "scripts\maintenance.py") clear-cache

if ($Retry.Count -gt 0) {
    $retryStr = $Retry -join ","
    Write-Host "----- Remove questions from checkpoint: $retryStr -----"
    & $py (Join-Path $root "scripts\maintenance.py") retry $retryStr
} else {
    Write-Host "(No retry list. For full eval: delete app\eval_agent_checkpoint.json first.)"
}

Write-Host "===== [5/5] Run evaluation ====="
if ($SkipEval) {
    Write-Host "(SkipEval: service is up and cache cleared. Run eval manually if needed.)"
} else {
    & $py (Join-Path $root "app\eval_agent.py")
}
