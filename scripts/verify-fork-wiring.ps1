#requires -Version 5
<#
.SYNOPSIS
    Verify every fork-only customization is still wired up.

.DESCRIPTION
    Single-command gate for upstream-sync hygiene. Runs:

      * the fork-features manifest meta-test
      * every existing source-grep wiring test (test_*_wiring.py)
      * every helper unit test referenced by the manifest

    Designed to be run BEFORE and AFTER any upstream merge / rebase /
    replay. If the BEFORE run is green and the AFTER run is red, the
    failing assertions point at exactly which fork patches were dropped.

    See FORK_NOTES.md > Fork Management Contract.

.PARAMETER PythonExe
    Optional override for the Python interpreter to use. Defaults to
    the workspace .venv interpreter.

.PARAMETER ReportPath
    Optional. When set, writes the full pytest output to this file
    relative to the fork repo root. Useful for capturing the BEFORE /
    AFTER sync runs side by side.

.EXAMPLE
    pwsh ./scripts/verify-fork-wiring.ps1

.EXAMPLE
    pwsh ./scripts/verify-fork-wiring.ps1 -ReportPath ../debug-repro/verify-fork-wiring-before.log
#>

[CmdletBinding()]
param(
    [string] $PythonExe = 'c:/Users/it/openwebui/.venv/Scripts/python.exe',
    [string] $ReportPath
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot
try {
    $env:PYTHONPATH = 'backend'

    $manifestPath = Join-Path $repoRoot 'fork-features.json'
    if (-not (Test-Path $manifestPath)) {
        throw "fork-features.json not found at $manifestPath"
    }

    $testTargets = New-Object System.Collections.Generic.List[string]
    $testTargets.Add('backend/open_webui/test/util/test_fork_features_manifest.py') | Out-Null

    # General, codebase-wide guard against the "caller kept, callee patch
    # dropped" failure mode (the get_web_loader(timeout=) regression). It is not
    # a *_wiring.py file, so add it explicitly here so auto-discovery cannot
    # silently skip it.
    $testTargets.Add('backend/open_webui/test/util/test_no_kwarg_signature_drift.py') | Out-Null

    # Auto-discover every wiring test on disk.
    Get-ChildItem -Path 'backend/open_webui/test/util' -Filter 'test_*_wiring.py' |
        Sort-Object Name |
        ForEach-Object {
            $rel = "backend/open_webui/test/util/$($_.Name)"
            if (-not $testTargets.Contains($rel)) { $testTargets.Add($rel) | Out-Null }
        }

    # Pull supporting unit tests out of the manifest so this script is the
    # single command operators have to remember.
    $manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json
    foreach ($feature in $manifest.fork_features) {
        foreach ($unitTest in $feature.supporting_unit_tests) {
            if (-not $testTargets.Contains($unitTest)) {
                $testTargets.Add($unitTest) | Out-Null
            }
        }
    }

    Write-Host "Running $($testTargets.Count) fork-wiring test target(s):"
    foreach ($t in $testTargets) { Write-Host "  - $t" }

    $pytestArgs = @('-m', 'pytest', '-q') + $testTargets
    if ($ReportPath) {
        & $PythonExe $pytestArgs 2>&1 | Tee-Object -FilePath $ReportPath
    } else {
        & $PythonExe $pytestArgs
    }
    $exit = $LASTEXITCODE
    if ($exit -ne 0) {
        Write-Error "fork-wiring verification failed (exit code $exit). See FORK_NOTES.md > Fork Management Contract for the recovery checklist."
        exit $exit
    }
    Write-Host 'Fork wiring verification passed.' -ForegroundColor Green
}
finally {
    Pop-Location
}
