[CmdletBinding()]
param(
    [ValidateSet("install", "uninstall", "status")]
    [string] $Action = "install",

    [string] $Source = "",

    [string] $BaseUrl = "https://raw.githubusercontent.com/yyykf/spellbook-skills/main/hooks",

    [switch] $Help
)

$ErrorActionPreference = "Stop"

if ($Help) {
    @"
Install the optional Spellbook Project Context Hook for Codex and Copilot.

Wraps hooks/install.py so you can install the hook WITHOUT cloning the repo.
Claude Code does not need this - it auto-loads the plugin hook. Only Codex /
Copilot require this step.

Usage:
  install-project-context-hook.ps1 [-Action install|uninstall|status]
  install-project-context-hook.ps1 -Source .\hooks [-Action status]

Options:
  -Action    install (default), uninstall, or status.
  -Source    Local hooks directory containing install.py and its payload files.
             If omitted, uses the checkout-local hooks directory when available,
             otherwise downloads from GitHub raw URLs.
  -BaseUrl   Remote base URL for downloads. Defaults to the main branch.
  -Help      Show this help.

After installing on Codex, start Codex and run /hooks once to trust the hook.
Requires py / python / python3 on PATH.
"@ | Write-Output
    exit 0
}

$Files = @("install.py", "session-start", "project-context.md")

# install.py needs a WORKING interpreter. On Windows "python3" is frequently an
# unusable stub that Get-Command still reports - a cygwin symlink the native
# shell cannot exec, or a Microsoft Store 0-byte alias - so probe candidates by
# actually running "--version" and take the first that succeeds. Order: the py
# launcher (most reliable on Windows), then python, then python3 (the usual name
# on macOS / Linux, where py does not exist).
function Test-Python($exe, $pre) {
    try {
        & $exe @($pre) "--version" *> $null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}
function Resolve-Python {
    $candidates = @(
        @{ Exe = "py";      Pre = @("-3") },
        @{ Exe = "python";  Pre = @() },
        @{ Exe = "python3"; Pre = @() }
    )
    foreach ($c in $candidates) {
        if ((Get-Command $c.Exe -ErrorAction SilentlyContinue) -and (Test-Python $c.Exe $c.Pre)) {
            return [pscustomobject]@{ Exe = $c.Exe; Pre = $c.Pre }
        }
    }
    throw "py / python / python3 is required to run the Project Context Hook installer (no working interpreter found)"
}
$python = Resolve-Python

# Prefer a local checkout when present (this script lives in scripts/, hooks/ is a sibling).
if (-not $Source -and $PSScriptRoot) {
    $candidate = Join-Path (Split-Path -Parent $PSScriptRoot) "hooks"
    if (Test-Path -LiteralPath (Join-Path $candidate "install.py") -PathType Leaf) {
        $Source = $candidate
    }
}

if ($Source) {
    $installPy = Join-Path $Source "install.py"
    if (-not (Test-Path -LiteralPath $installPy -PathType Leaf)) {
        throw "install.py not found in source directory: $Source"
    }
    & $python.Exe @($python.Pre) $installPy $Action
    exit $LASTEXITCODE
}

# No local checkout: download install.py and its payload into a temp dir, then run it there.
$workDir = Join-Path ([System.IO.Path]::GetTempPath()) ("spellbook-pc-hook." + [System.Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $workDir | Out-Null
try {
    foreach ($file in $Files) {
        Invoke-WebRequest -Uri "$($BaseUrl.TrimEnd('/'))/$file" -OutFile (Join-Path $workDir $file) -UseBasicParsing
    }
    & $python.Exe @($python.Pre) (Join-Path $workDir "install.py") $Action
    exit $LASTEXITCODE
} finally {
    Remove-Item -Recurse -Force -LiteralPath $workDir -ErrorAction SilentlyContinue
}
