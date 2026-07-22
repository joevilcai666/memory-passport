[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

function Read-RepositoryFiles {
    param([string[]]$RelativePaths)

    foreach ($relativePath in $RelativePaths) {
        $path = Join-Path $repositoryRoot $relativePath
        if (Test-Path -LiteralPath $path -PathType Leaf) {
            Get-Item -LiteralPath $path
            continue
        }
        Get-ChildItem -LiteralPath $path -Recurse -File
    }
}

function Find-Pattern {
    param(
        [System.IO.FileInfo[]]$Files,
        [string]$Pattern
    )

    foreach ($file in $Files) {
        $content = Get-Content -LiteralPath $file.FullName -Raw -Encoding utf8
        if ($content -match $Pattern) {
            $relative = $file.FullName.Substring($repositoryRoot.Length).TrimStart("\", "/")
            [PSCustomObject]@{ File = $relative; Pattern = $Pattern }
        }
    }
}

$frontendFiles = @(Read-RepositoryFiles -RelativePaths @("src/app", "src/components")) |
    Where-Object { $_.Extension -in @(".ts", ".tsx") -and $_.Name -notmatch "\.test\." }
$activeDocs = @(Read-RepositoryFiles -RelativePaths @(
    "README.md",
    "CUSTOMER_QUICKSTART.zh-CN.md",
    "B2B_CUSTOMER_GUIDE.zh-CN.md",
    "docs/local-evaluation.md",
    "docs/real-hms.md",
    "CLAUDE.md"
))

$violations = @()
$violations += Find-Pattern -Files $frontendFiles -Pattern "/console/memory/debugger"
$violations += Find-Pattern -Files $activeDocs -Pattern "(?im)(--branch\s+HMS|git\s+checkout\s+HMS)"
$violations += Find-Pattern -Files @(Get-Item (Join-Path $repositoryRoot "src/app/page.tsx")) -Pattern "(?i)no real backend"
$violations += Find-Pattern -Files $frontendFiles -Pattern "(?s)onClick=\{\(\)\s*=>\s*\{?\s*toast(?:\.(?:success|error))?\([^;]+;?\s*\}?\}"
$violations += Find-Pattern -Files $frontendFiles -Pattern "(?s)setTimeout\([^)]*router\.(?:push|replace)"

if ($violations.Count -gt 0) {
    Write-Error ("Product claim/source check failed:`n" + (($violations | ForEach-Object {
        "- {0} matched {1}" -f $_.File, $_.Pattern
    }) -join "`n"))
}

Write-Host "Product claim/source check passed."
