param(
    [Parameter(Position = 0)]
    [ValidateSet(
        "env-init", "config", "build-runner", "build", "up", "up-cache",
        "down", "restart", "status", "logs", "health", "db-check",
        "test-win", "test-linux", "backup-db", "restore-db", "help"
    )]
    [string]$Command = "help",

    [Parameter(Position = 1)]
    [string]$Target = "",

    [switch]$ConfirmRestore,

    [string]$WslDistro = "Ubuntu-24.04"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$GodotConsole = Join-Path $RepoRoot "tools\godot\Godot_v4.4-stable_win64_console.exe"

function Show-Usage {
    @"
Uso: .\infrastructure\scripts\playforge.ps1 <comando> [alvo] [-ConfirmRestore]

Comandos Windows / Gerais:
  test-win                         Executa suite Godot headless nativa no Windows
  env-init                         Cria .env local via WSL2 (nao sobrescreve existente)
  config                           Valida docker-compose.yml via WSL2
  build-runner | build             Constroi imagem factory-runner no Docker/WSL2
  up | up-cache | down | restart   Gerencia containers PlayForge no Docker/WSL2
  status | logs [servico]          Inspeciona containers PlayForge
  health | db-check                Verifica PostgreSQL + extensao pgvector
  test-linux                       Executa suite Godot headless dentro do container Linux
  backup-db [arquivo.sql]          Gera backup SQL em build/backups/
  restore-db <arquivo> -ConfirmRestore
                                   Restaura backup SQL (exige -ConfirmRestore)
"@
}

function Invoke-GodotWinSuite {
    if (-not (Test-Path $GodotConsole)) {
        throw "Binario Godot Windows console nao encontrado em: $GodotConsole"
    }
    $tempRunDir = Join-Path ([System.IO.Path]::GetTempPath()) "playforge_win_test"
    New-Item -ItemType Directory -Force -Path $tempRunDir | Out-Null
    $verifySave = Join-Path $tempRunDir "playforge_win_boot_verify.json"
    $previousAppData = $env:APPDATA
    $env:APPDATA = $tempRunDir

    try {
        Write-Host "=== Godot Windows Version ==="
        & $GodotConsole --headless --version
        if ($LASTEXITCODE -ne 0) { throw "Falha ao consultar versao Godot Windows." }

        Write-Host "=== Unit Tests (Windows Headless) ==="
        & $GodotConsole --headless --no-header --path $RepoRoot --script res://tests/unit/run_unit_tests.gd
        if ($LASTEXITCODE -ne 0) { throw "Falha em run_unit_tests.gd no Windows." }

        Write-Host "=== Action Balance Verifier (Windows Headless) ==="
        & $GodotConsole --headless --no-header --path $RepoRoot --script res://tests/integration/run_action_verifier.gd
        if ($LASTEXITCODE -ne 0) { throw "Falha em run_action_verifier.gd no Windows." }

        Write-Host "=== Engine Boot Gate (Windows Headless) ==="
        & $GodotConsole --headless --no-header --path $RepoRoot --script res://tests/integration/verify_engine_boot.gd -- --save-path=$verifySave
        if ($LASTEXITCODE -ne 0) { throw "Falha em verify_engine_boot.gd no Windows." }
    } finally {
        $env:APPDATA = $previousAppData
    }
}

function Convert-ToWslPath([string]$PathValue) {
    if ([string]::IsNullOrWhiteSpace($PathValue)) { return "" }
    if ($PathValue -match '^[A-Za-z]:\\') {
        $drive = $PathValue.Substring(0, 1).ToLowerInvariant()
        $rest = $PathValue.Substring(2).Replace('\', '/')
        return "/mnt/$drive$rest"
    }
    return $PathValue.Replace('\', '/')
}

switch ($Command) {
    "help" {
        Show-Usage
        exit 0
    }
    "test-win" {
        Invoke-GodotWinSuite
        exit 0
    }
    "restore-db" {
        if ([string]::IsNullOrWhiteSpace($Target)) {
            throw "Informe o arquivo SQL de backup em -Target."
        }
        if (-not $ConfirmRestore) {
            throw "BLOQUEADO (fail-closed): passe -ConfirmRestore explicitamente para restaurar o banco."
        }
        $wslScript = Convert-ToWslPath (Join-Path $PSScriptRoot "playforge.sh")
        $wslTarget = Convert-ToWslPath $Target
        & wsl.exe -d $WslDistro -- bash $wslScript restore-db $wslTarget --confirm-restore
        exit $LASTEXITCODE
    }
    default {
        $wslScript = Convert-ToWslPath (Join-Path $PSScriptRoot "playforge.sh")
        $argsList = @("-d", $WslDistro, "--", "bash", $wslScript, $Command)
        if (-not [string]::IsNullOrWhiteSpace($Target)) {
            if ($Command -eq "backup-db") {
                $argsList += (Convert-ToWslPath $Target)
            } else {
                $argsList += $Target
            }
        }
        & wsl.exe @argsList
        exit $LASTEXITCODE
    }
}
