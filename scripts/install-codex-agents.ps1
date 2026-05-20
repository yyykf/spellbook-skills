[CmdletBinding()]
param(
    [ValidateSet("project", "user")]
    [string] $Scope = "project",

    [string] $Source = "",

    [string] $BaseUrl = "https://raw.githubusercontent.com/yyykf/spellbook-skills/main/codex-agents/spellbook",

    [switch] $Force,

    [switch] $DryRun
)

$ErrorActionPreference = "Stop"

$Files = @(
    "spellbook-code-quality-reviewer.toml",
    "spellbook-code-reuse-reviewer.toml",
    "spellbook-code-efficiency-reviewer.toml"
)

if ($Scope -eq "user") {
    $codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
    $targetDir = Join-Path $codexHome "agents/spellbook"
} else {
    $targetDir = Join-Path (Get-Location) ".codex/agents/spellbook"
}

if (-not $Source -and $PSScriptRoot) {
    $candidateSource = Join-Path (Split-Path -Parent $PSScriptRoot) "codex-agents/spellbook"
    if (Test-Path -LiteralPath $candidateSource -PathType Container) {
        $Source = $candidateSource
    }
}

$useLocalSource = $false
if ($Source) {
    if (-not (Test-Path -LiteralPath $Source -PathType Container)) {
        throw "Source directory does not exist: $Source"
    }
    $useLocalSource = $true
}

foreach ($file in $Files) {
    $dest = Join-Path $targetDir $file
    if ((Test-Path -LiteralPath $dest) -and -not $Force) {
        throw "Target file already exists: $dest. Rerun with -Force to overwrite."
    }
}

if ($DryRun) {
    Write-Output "Would install Spellbook Codex agents to: $targetDir"
    exit 0
}

New-Item -ItemType Directory -Force -Path $targetDir | Out-Null

foreach ($file in $Files) {
    $dest = Join-Path $targetDir $file
    $tmp = Join-Path $targetDir (".$file.tmp.$PID")

    if ($useLocalSource) {
        $src = Join-Path $Source $file
        if (-not (Test-Path -LiteralPath $src -PathType Leaf)) {
            throw "Source file does not exist: $src"
        }
        Copy-Item -LiteralPath $src -Destination $tmp -Force
    } else {
        Invoke-WebRequest -Uri "$($BaseUrl.TrimEnd('/'))/$file" -OutFile $tmp
    }

    Move-Item -LiteralPath $tmp -Destination $dest -Force
}

Write-Output "Installed Spellbook Codex agents to: $targetDir"
