[CmdletBinding()]
param(
    [string]$ApiUrl = "http://127.0.0.1:8000",
    [string]$HmsApiUrl = "http://127.0.0.1:18080",
    [string]$ApiKey = "mp_sandbox_LK39sn8vQ4x2pR7wY1tBz0Hd",
    [string]$HmsApiKey = "hms_tenant_luna_change_me",
    [string]$ResultPath = "artifacts/remediation-2026-07-22/api-results.json"
)

$ErrorActionPreference = "Stop"
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pythonPath = Join-Path $repositoryRoot "backend/.venv/Scripts/python.exe"
$matrixPath = Join-Path $repositoryRoot "scripts/live-api-matrix.py"
$absoluteResultPath = Join-Path $repositoryRoot $ResultPath
$resultDirectory = Split-Path -Parent $absoluteResultPath

function Assert-True {
    param(
        [bool]$Condition,
        [string]$Message
    )
    if (-not $Condition) {
        throw $Message
    }
}

function Invoke-PsqlScalar {
    param([string]$Sql)

    $value = & docker compose exec -T postgres psql -U mp -d memory_passport -Atc $Sql
    if ($LASTEXITCODE -ne 0) {
        throw "PostgreSQL assertion query failed: $Sql"
    }
    return ($value | Select-Object -Last 1).Trim()
}

if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    throw "Backend virtual environment is missing at $pythonPath"
}
if (-not (Test-Path -LiteralPath $matrixPath -PathType Leaf)) {
    throw "Live API matrix is missing at $matrixPath"
}
New-Item -ItemType Directory -Force -Path $resultDirectory | Out-Null

Push-Location $repositoryRoot
try {
    $health = Invoke-RestMethod -Uri "$ApiUrl/v1/health" -Method Get
    Assert-True ($health.mp -eq "ok" -and $health.hms -eq "ok" -and $health.db -eq "ok") `
        "The live stack is not healthy."

    $allowedOrigin = "http://localhost:3000"
    $preflight = Invoke-WebRequest -UseBasicParsing -Uri "$ApiUrl/v1/memories" -Method Options -Headers @{
        Origin = $allowedOrigin
        "Access-Control-Request-Method" = "GET"
        "Access-Control-Request-Headers" = "authorization"
    }
    Assert-True ($preflight.StatusCode -eq 200) "Allowed CORS preflight did not return 200."
    Assert-True ($preflight.Headers["Access-Control-Allow-Origin"] -eq $allowedOrigin) `
        "Allowed CORS origin was not echoed."
    Assert-True ($preflight.Headers["Access-Control-Allow-Headers"] -match "authorization") `
        "Authorization was not allowed by CORS."

    $blockedOrigin = "https://unlisted.example"
    $blockedStatus = $null
    $blockedAllowOrigin = $null
    try {
        $blocked = Invoke-WebRequest -UseBasicParsing -Uri "$ApiUrl/v1/memories" -Method Options -Headers @{
            Origin = $blockedOrigin
            "Access-Control-Request-Method" = "GET"
            "Access-Control-Request-Headers" = "authorization"
        }
        $blockedStatus = $blocked.StatusCode
        $blockedAllowOrigin = $blocked.Headers["Access-Control-Allow-Origin"]
    } catch {
        $blockedStatus = [int]$_.Exception.Response.StatusCode
        $blockedAllowOrigin = $_.Exception.Response.Headers["Access-Control-Allow-Origin"]
    }
    Assert-True ($blockedStatus -ge 400) "An unlisted CORS origin was unexpectedly accepted."
    Assert-True ([string]::IsNullOrEmpty($blockedAllowOrigin)) `
        "An unlisted CORS origin received Access-Control-Allow-Origin."

    $env:MP_API_URL = $ApiUrl
    $env:HMS_API_URL = $HmsApiUrl
    $env:MP_API_KEY = $ApiKey
    $env:HMS_API_KEY = $HmsApiKey
    $env:MP_MATRIX_RESULT_PATH = $absoluteResultPath
    & $pythonPath $matrixPath
    if ($LASTEXITCODE -ne 0) {
        throw "Live API matrix failed. See $ResultPath"
    }

    $summary = Get-Content -LiteralPath $absoluteResultPath -Raw -Encoding utf8 | ConvertFrom-Json
    Assert-True ($summary.failed -eq 0 -and $summary.error -eq $null) `
        "Live API matrix reported failures."
    $run = [string]$summary.run
    Assert-True ($run -match '^matrix-[a-f0-9]{10}$') "Unexpected matrix run identifier: $run"

    $feedbackResult = $summary.results | Where-Object { $_.name -eq "persist trace feedback" } | Select-Object -First 1
    $traceId = [string]$feedbackResult.body.id
    Assert-True (-not [string]::IsNullOrEmpty($traceId)) "Trace feedback result did not expose a trace id."

    $databaseChecks = @(
        [PSCustomObject]@{
            name = "created app persisted"
            value = Invoke-PsqlScalar "select count(*) from apps where name = '$run';"
            expected = "1"
        },
        [PSCustomObject]@{
            name = "deleted passport persisted"
            value = Invoke-PsqlScalar "select count(*) from users where external_user_id = '$run' and passport_status = 'deleted';"
            expected = "1"
        },
        [PSCustomObject]@{
            name = "migration rollback persisted"
            value = Invoke-PsqlScalar "select count(*) from migrations m join users u on u.id = m.user_id where u.external_user_id = '$run' and m.status = 'rolled_back';"
            expected = "1"
        },
        [PSCustomObject]@{
            name = "team invite consumed"
            value = Invoke-PsqlScalar "select count(*) from team_invites where email = '$run@example.com' and accepted_at is not null;"
            expected = "1"
        },
        [PSCustomObject]@{
            name = "trace feedback persisted"
            value = Invoke-PsqlScalar "select count(*) from retrieval_traces where id = '$traceId' and feedback::text like '%useful%';"
            expected = "1"
        }
    )
    foreach ($check in $databaseChecks) {
        Assert-True ($check.value -eq $check.expected) `
            "Database assertion '$($check.name)' expected $($check.expected), got $($check.value)."
    }

    $summary | Add-Member -NotePropertyName cors -NotePropertyValue ([PSCustomObject]@{
        allowed_origin = $allowedOrigin
        allowed_status = $preflight.StatusCode
        blocked_origin = $blockedOrigin
        blocked_status = $blockedStatus
    }) -Force
    $summary | Add-Member -NotePropertyName database_checks -NotePropertyValue $databaseChecks -Force
    $summary | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $absoluteResultPath -Encoding utf8

    Write-Host "Remediation matrix passed: $($summary.passed)/$($summary.total) API assertions plus CORS and $($databaseChecks.Count) database assertions."
    Write-Host "Evidence: $ResultPath"
} finally {
    Pop-Location
}
