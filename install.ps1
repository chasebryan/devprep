# Run from a downloaded checkout, using Windows PowerShell 5.1 or PowerShell 7.
$ErrorActionPreference = 'Stop'
$devprepArgs = $args
$preview = @($devprepArgs | Where-Object { $_ -in @('--dry-run', '--json', '--list', '--help', '-h', '--version') }).Count -gt 0
$assumeYes = @($devprepArgs | Where-Object { $_ -in @('--yes', '-y') }).Count -gt 0
$env:PYTHONDONTWRITEBYTECODE = '1'

function Find-DevprepPython {
    $candidates = @()
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $result = & py -3 -c 'import sys; print(sys.executable) if sys.version_info >= (3, 9) else None' 2>$null
        if ($LASTEXITCODE -eq 0 -and $result) { $candidates += $result }
    }
    # Avoid WindowsApps execution aliases which can launch the Microsoft Store.
    foreach ($name in @('python3', 'python')) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command -and $command.Source -notlike '*\WindowsApps\*') { $candidates += $command.Source }
    }
    foreach ($root in @("$env:LOCALAPPDATA\Programs\Python", "$env:ProgramFiles\Python313")) {
        if (Test-Path $root) {
            $candidates += @(Get-ChildItem $root -Filter python.exe -Recurse -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
        }
    }
    foreach ($candidate in $candidates) {
        & $candidate -c 'import sys; sys.exit(sys.version_info < (3, 9))' 2>$null
        if ($LASTEXITCODE -eq 0) { return $candidate }
    }
    return $null
}

$python = Find-DevprepPython
if (-not $python) {
    if ($preview) { throw 'Python 3.9+ is required to preview. Nothing was installed.' }
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw 'Install or update Microsoft App Installer (WinGet), then rerun: https://learn.microsoft.com/windows/package-manager/winget/'
    }
    if (-not $assumeYes) {
        $answer = Read-Host 'devprep needs Python 3.13. Install it with WinGet? [Y/n]'
        if ($answer -and $answer -notmatch '^(y|yes)$') { exit 0 }
    }
    & winget install --id Python.Python.3.13 --exact --source winget --silent --no-upgrade --accept-package-agreements --accept-source-agreements --disable-interactivity
    if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne -1978335189) { throw "Python installation failed: $LASTEXITCODE" }
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
    $python = Find-DevprepPython
    if (-not $python) { throw 'Python was installed but could not be located. Open a new terminal and rerun.' }
}

Push-Location $PSScriptRoot
try {
    & $python -m devprep @devprepArgs
    $devprepExitCode = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $devprepExitCode
