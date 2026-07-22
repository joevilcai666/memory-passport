param(
    [string]$RepositoryRoot = ""
)

$ErrorActionPreference = "Stop"

if (-not $RepositoryRoot) {
    $RepositoryRoot = (& git rev-parse --show-toplevel).Trim()
}
$RepositoryRoot = [System.IO.Path]::GetFullPath($RepositoryRoot)

$tracked = @(& git -C $RepositoryRoot ls-files)
if ($LASTEXITCODE -ne 0) {
    throw "Unable to list tracked files in $RepositoryRoot"
}

$entrypoints = @(
    $tracked | Where-Object {
        $_ -match '\.sh$' -or $_ -match '(^|/)Dockerfile$'
    }
)

if ($entrypoints.Count -eq 0) {
    throw "No tracked shell scripts or Dockerfiles were found"
}

$invalid = [System.Collections.Generic.List[string]]::new()
foreach ($relativePath in $entrypoints) {
    $absolutePath = Join-Path $RepositoryRoot $relativePath
    $bytes = [System.IO.File]::ReadAllBytes($absolutePath)
    for ($index = 0; $index -lt ($bytes.Length - 1); $index++) {
        if ($bytes[$index] -eq 13 -and $bytes[$index + 1] -eq 10) {
            $invalid.Add($relativePath)
            break
        }
    }
}

if ($invalid.Count -gt 0) {
    Write-Error (
        "CRLF detected in Linux entrypoints:`n - " +
        (($invalid | Sort-Object -Unique) -join "`n - ")
    )
    exit 1
}

Write-Output "LF verification passed for $($entrypoints.Count) Linux entrypoints."
