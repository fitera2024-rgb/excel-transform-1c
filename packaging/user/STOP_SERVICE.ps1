$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
try {
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [Console]::OutputEncoding = $utf8
    $OutputEncoding = $utf8
} catch {
}

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $root
$runtimeDirectory = if ($env:OPIU_RUNTIME_DIR) { $env:OPIU_RUNTIME_DIR } else { Join-Path $root "runtime" }

function Get-ListenerProcessIds {
    param([int]$Port)
    $connections = @(
        Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
    )
    return @($connections | Select-Object -ExpandProperty OwningProcess -Unique)
}

function Test-IsOpiuServiceProcess {
    param(
        [int]$ProcessId,
        [int]$Port
    )
    try {
        $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction Stop
        if ([string]$processInfo.CommandLine -match "excel_transform_1c") {
            return $true
        }
    } catch {
    }

    if ($Port -gt 0) {
        try {
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 1
            if ($health.status -eq "ok") {
                $homeResponse = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$Port/" -TimeoutSec 2
                return $homeResponse.StatusCode -eq 200 -and $homeResponse.Content -match "OPIU"
            }
        } catch {
        }
    }
    return $false
}

$ports = New-Object 'System.Collections.Generic.List[int]'
foreach ($port in @(8000, 8765, 8001, 8010, 8080)) {
    $ports.Add($port)
}
$serviceUrlPath = Join-Path $runtimeDirectory "service.url"
if (Test-Path -LiteralPath $serviceUrlPath) {
    try {
        $savedUrl = [Uri](Get-Content -LiteralPath $serviceUrlPath -Raw)
        if (-not $ports.Contains($savedUrl.Port)) {
            $ports.Insert(0, $savedUrl.Port)
        }
    } catch {
    }
}

$targets = @{}
$pidPath = Join-Path $runtimeDirectory "service.pid"
if (Test-Path -LiteralPath $pidPath) {
    try {
        $savedProcessId = [int](Get-Content -LiteralPath $pidPath -Raw)
        $targets[$savedProcessId] = 0
    } catch {
    }
}
foreach ($port in $ports) {
    foreach ($processId in (Get-ListenerProcessIds $port)) {
        $targets[$processId] = $port
    }
}

$stopped = 0
foreach ($entry in $targets.GetEnumerator()) {
    $processId = [int]$entry.Key
    $port = [int]$entry.Value
    if ($processId -le 0 -or $processId -eq $PID) {
        continue
    }
    if (Test-IsOpiuServiceProcess $processId $port) {
        try {
            Stop-Process -Id $processId -Force -ErrorAction Stop
            Write-Host "Остановлен Excel -> OPIU Light (PID $processId)." -ForegroundColor Green
            $stopped += 1
        } catch {
            Write-Host "Не удалось остановить PID ${processId}: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
}

Remove-Item -LiteralPath $pidPath -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $serviceUrlPath -Force -ErrorAction SilentlyContinue

if ($stopped -eq 0) {
    Write-Host "Работающий Excel -> OPIU Light не найден."
}
Write-Host "Готово."
