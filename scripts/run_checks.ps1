$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

rtk .\.venv\Scripts\python.exe -m pytest -m "not live and not e2e" -q
rtk .\.venv\Scripts\python.exe -m ruff check app.py nivesh scripts tests
rtk .\.venv\Scripts\python.exe -m mypy nivesh scripts
rtk .\.venv\Scripts\python.exe -m pip_audit -r requirements.txt
rtk npm ci
rtk npm run build:component
$firstHash = rtk node -e "const fs=require('fs'),c=require('crypto');process.stdout.write(c.createHash('sha256').update(fs.readFileSync('nivesh/components/assets/towers.js')).digest('hex'))"
rtk npm run build:component
$secondHash = rtk node -e "const fs=require('fs'),c=require('crypto');process.stdout.write(c.createHash('sha256').update(fs.readFileSync('nivesh/components/assets/towers.js')).digest('hex'))"
if ($firstHash -ne $secondHash) {
    throw "Component build is not deterministic."
}
rtk npm audit
rtk git diff --check

$listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
$listener.Start()
$port = ([System.Net.IPEndPoint]$listener.LocalEndpoint).Port
$listener.Stop()
$appUrl = "http://127.0.0.1:$port"
$previousDemo = $env:NIVESH_DEMO_MODE
$previousBaseUrl = $env:NIVESH_E2E_BASE_URL
$env:NIVESH_DEMO_MODE = "true"
$env:NIVESH_E2E_BASE_URL = $appUrl
$server = Start-Process -FilePath "rtk" -ArgumentList @(
    ".\.venv\Scripts\python.exe",
    "-m", "streamlit", "run", "app.py",
    "--server.port=$port",
    "--server.address=127.0.0.1",
    "--server.headless=true",
    "--browser.gatherUsageStats=false"
) -PassThru -WindowStyle Hidden

try {
    $ready = $false
    for ($attempt = 0; $attempt -lt 120; $attempt++) {
        if ($server.HasExited) {
            throw "Streamlit exited before becoming healthy."
        }
        try {
            $response = Invoke-WebRequest -Uri "$appUrl/_stcore/health" -TimeoutSec 1 -UseBasicParsing
            if ($response.StatusCode -eq 200) {
                $ready = $true
                break
            }
        }
        catch {
            Start-Sleep -Milliseconds 250
        }
    }
    if (-not $ready) {
        throw "Streamlit health endpoint was not ready within 30 seconds."
    }
    rtk .\.venv\Scripts\python.exe -m pytest tests/e2e/test_app.py -m e2e -q
}
finally {
    if (-not $server.HasExited) {
        Stop-Process -Id $server.Id -Force
        $server.WaitForExit()
    }
    $env:NIVESH_DEMO_MODE = $previousDemo
    $env:NIVESH_E2E_BASE_URL = $previousBaseUrl
}
