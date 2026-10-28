$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)

function Invoke-Checked([scriptblock]$Command) {
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Release check failed with exit code ${LASTEXITCODE}: $Command"
    }
}

Invoke-Checked { rtk proxy .\.venv\Scripts\python.exe -m pytest -m "not live and not e2e" -q }
Invoke-Checked { rtk proxy .\.venv\Scripts\python.exe -m ruff check app.py nivesh scripts tests }
Invoke-Checked { rtk proxy .\.venv\Scripts\python.exe -m mypy nivesh scripts }
Invoke-Checked { rtk proxy .\.venv\Scripts\python.exe -m pip_audit -r requirements.txt }
Invoke-Checked { rtk proxy npm ci }
Invoke-Checked { rtk proxy npm run build:component }
$firstHash = Invoke-Checked {
    rtk proxy node -e "const fs=require('fs'),c=require('crypto');process.stdout.write(c.createHash('sha256').update(fs.readFileSync('nivesh/components/assets/towers.js')).digest('hex'))"
}
Invoke-Checked { rtk proxy npm run build:component }
$secondHash = Invoke-Checked {
    rtk proxy node -e "const fs=require('fs'),c=require('crypto');process.stdout.write(c.createHash('sha256').update(fs.readFileSync('nivesh/components/assets/towers.js')).digest('hex'))"
}
if ($firstHash -ne $secondHash) {
    throw "Component build is not deterministic."
}
Invoke-Checked { rtk proxy npm audit }
Invoke-Checked { rtk proxy git diff --check }

# The fixture starts and terminates its own local demo process on a free port.
$previousBaseUrl = $env:NIVESH_E2E_BASE_URL
Remove-Item Env:NIVESH_E2E_BASE_URL -ErrorAction SilentlyContinue
try {
    Invoke-Checked { rtk proxy .\.venv\Scripts\python.exe -m pytest tests/e2e/test_app.py -m e2e -q }
}
finally {
    if ($null -ne $previousBaseUrl) {
        $env:NIVESH_E2E_BASE_URL = $previousBaseUrl
    }
}
