[CmdletBinding()]
param(
    [ValidateSet("install", "uninstall", "status")]
    [string] $Action = "install",

    [ValidateSet("", "copilot", "codex-fallback", "all", "auto")]
    [string] $Target = "",

    [string] $Source = "",

    [string] $BaseUrl = "https://raw.githubusercontent.com/yyykf/spellbook-skills/main/hooks",

    [switch] $Help
)

$ErrorActionPreference = "Stop"

if ($Help) {
    @"
Install the optional Spellbook Project Context Hook for Copilot and older Codex fallback.

Wraps hooks/install.py so you can install the hook WITHOUT cloning the repo.
Claude Code and Codex 0.137.0+ auto-load the plugin hook.
Use -Target auto to let the script install Codex fallback only when it can
confirm an older Codex version; uncertain detection fails closed.

Usage:
  install-project-context-hook.ps1 [-Action install|uninstall|status] [-Target copilot|codex-fallback|all|auto]
  install-project-context-hook.ps1 -Source .\hooks [-Action status] [-Target copilot|codex-fallback|all|auto]

Options:
  -Action    install (default), uninstall, or status.
  -Target    Target platform. install defaults to copilot; uninstall/status
             default to all. auto is install-only and only writes Codex
             fallback when codex --version is confirmed below 0.137.0.
  -Source    Local hooks directory containing install.py and its payload files.
             If omitted, uses the checkout-local hooks directory when available,
             otherwise downloads from GitHub raw URLs.
  -BaseUrl   Remote base URL for downloads. Defaults to the main branch.
  -Help      Show this help.

For Codex fallback installs, start Codex and run /hooks once to trust the hook.
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

function Invoke-InstallPy($installPy) {
    $pythonArgs = @()
    $pythonArgs += $python.Pre
    $pythonArgs += $installPy
    $pythonArgs += $Action
    if ($Target) {
        $pythonArgs += "--target"
        $pythonArgs += $Target
    }
    & $python.Exe @pythonArgs
    exit $LASTEXITCODE
}

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
    Invoke-InstallPy $installPy
}

# No local checkout: download install.py and its payload into a temp dir, then run it there.
$workDir = Join-Path ([System.IO.Path]::GetTempPath()) ("spellbook-pc-hook." + [System.Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $workDir | Out-Null
try {
    foreach ($file in $Files) {
        Invoke-WebRequest -Uri "$($BaseUrl.TrimEnd('/'))/$file" -OutFile (Join-Path $workDir $file) -UseBasicParsing
    }
    Invoke-InstallPy (Join-Path $workDir "install.py")
} finally {
    Remove-Item -Recurse -Force -LiteralPath $workDir -ErrorAction SilentlyContinue
}
