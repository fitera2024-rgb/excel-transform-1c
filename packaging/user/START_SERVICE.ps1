param(
    [switch]$SmokeTest
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $root
$logPath = Join-Path $root "startup.log"
$transcriptStarted = $false
$exitCode = 0

try {
    try {
        Start-Transcript -LiteralPath $logPath -Append -Force | Out-Null
        $transcriptStarted = $true
    } catch {
        # The launcher still prints errors even when transcript is unavailable.
    }

    function Write-Stage {
        param([string]$Message)
        Write-Host ""
        Write-Host $Message -ForegroundColor Cyan
    }

    function Invoke-PythonCandidate {
        param(
            [string]$Executable,
            [string[]]$PrefixArguments,
            [string[]]$Arguments
        )
        $allArguments = @()
        $allArguments += $PrefixArguments
        $allArguments += $Arguments
        & $Executable @allArguments
        return $LASTEXITCODE
    }

    function Test-PythonCandidate {
        param(
            [string]$Executable,
            [string[]]$PrefixArguments
        )
        try {
            $code = "import struct,sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) and struct.calcsize('P') * 8 == 64 else 1)"
            $allArguments = @()
            $allArguments += $PrefixArguments
            $allArguments += @("-c", $code)
            & $Executable @allArguments *> $null
            return $LASTEXITCODE -eq 0
        } catch {
            return $false
        }
    }

    function Add-PythonCandidate {
        param(
            [System.Collections.Generic.List[object]]$Candidates,
            [string]$Executable,
            [string[]]$PrefixArguments,
            [string]$Label
        )
        if ([string]::IsNullOrWhiteSpace($Executable)) {
            return
        }
        $key = "$Executable|$($PrefixArguments -join ' ')"
        if (-not ($Candidates | Where-Object { $_.Key -eq $key })) {
            $Candidates.Add([pscustomobject]@{
                Key = $key
                Executable = $Executable
                PrefixArguments = $PrefixArguments
                Label = $Label
            })
        }
    }

    function Test-TcpPort {
        param([int]$Port)
        $client = New-Object System.Net.Sockets.TcpClient
        try {
            $result = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
            if (-not $result.AsyncWaitHandle.WaitOne(350)) {
                return $false
            }
            $client.EndConnect($result)
            return $true
        } catch {
            return $false
        } finally {
            $client.Dispose()
        }
    }

    function Wait-ServiceReady {
        param(
            [string]$HealthUrl,
            [int]$Attempts = 80
        )
        for ($attempt = 0; $attempt -lt $Attempts; $attempt++) {
            try {
                $healthResponse = Invoke-RestMethod -Uri $HealthUrl -TimeoutSec 1
                if ($healthResponse.status -eq "ok") {
                    return $true
                }
            } catch {
            }
            Start-Sleep -Milliseconds 500
        }
        return $false
    }

    Write-Stage "Excel -> OPIU Light: проверка локального запуска"
    Write-Host "Папка пакета: $root"
    Write-Host "Журнал запуска: $logPath"

    $candidates = New-Object 'System.Collections.Generic.List[object]'

    $pyCommand = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($pyCommand) {
        Add-PythonCandidate $candidates $pyCommand.Source @("-3.11") "Python Launcher 3.11"
    }

    $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        Add-PythonCandidate $candidates $pythonCommand.Source @() "python.exe из PATH"
    }

    $directPaths = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\python.exe"),
        (Join-Path $env:ProgramFiles "Python311\python.exe")
    )
    foreach ($directPath in $directPaths) {
        if (Test-Path -LiteralPath $directPath) {
            Add-PythonCandidate $candidates $directPath @() "Python 3.11 из стандартной папки"
        }
    }

    $registryPaths = @(
        "HKCU:\Software\Python\PythonCore\3.11\InstallPath",
        "HKLM:\Software\Python\PythonCore\3.11\InstallPath",
        "HKLM:\Software\WOW6432Node\Python\PythonCore\3.11\InstallPath"
    )
    foreach ($registryPath in $registryPaths) {
        try {
            if (Test-Path -LiteralPath $registryPath) {
                $installRoot = (Get-Item -LiteralPath $registryPath).GetValue("")
                if ($installRoot) {
                    $registryPython = Join-Path $installRoot "python.exe"
                    if (Test-Path -LiteralPath $registryPython) {
                        Add-PythonCandidate $candidates $registryPython @() "Python 3.11 из реестра"
                    }
                }
            }
        } catch {
        }
    }

    $selectedPython = $null
    foreach ($candidate in $candidates) {
        if (Test-PythonCandidate $candidate.Executable $candidate.PrefixArguments) {
            $selectedPython = $candidate
            break
        }
    }

    if (-not $selectedPython) {
        throw "Python 3.11 x64 не найден. Установите 64-bit Python 3.11. Пакет проверяет PATH, Python Launcher, стандартную папку и реестр."
    }

    Write-Host "Найден: $($selectedPython.Label)"
    Write-Host "Python: $($selectedPython.Executable) $($selectedPython.PrefixArguments -join ' ')"

    $venvDirectory = Join-Path $root ".venv"
    $venvPython = Join-Path $venvDirectory "Scripts\python.exe"
    $packageMarker = Join-Path $root "PACKAGE_BUILD.txt"
    $venvMarker = Join-Path $venvDirectory "PACKAGE_BUILD.txt"
    $wheelDirectory = Join-Path $root "wheels"

    if (-not (Test-Path -LiteralPath $packageMarker)) {
        throw "В пакете отсутствует PACKAGE_BUILD.txt. Распакуйте исходный ZIP заново."
    }
    if (-not (Test-Path -LiteralPath $wheelDirectory)) {
        throw "В пакете отсутствует папка wheels. Распакуйте исходный ZIP полностью."
    }

    $needInstall = -not (Test-Path -LiteralPath $venvPython)
    if (-not $needInstall) {
        & $venvPython -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)" *> $null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Старое локальное окружение несовместимо; оно будет создано заново."
            Remove-Item -LiteralPath $venvDirectory -Recurse -Force
            $needInstall = $true
        }
    }

    if (-not $needInstall) {
        if (-not (Test-Path -LiteralPath $venvMarker)) {
            $needInstall = $true
        } else {
            $currentBuild = Get-Content -LiteralPath $packageMarker -Raw
            $installedBuild = Get-Content -LiteralPath $venvMarker -Raw
            if ($currentBuild -ne $installedBuild) {
                $needInstall = $true
            }
        }
    }

    if ($needInstall) {
        Write-Stage "Подготовка локального окружения"
        if (-not (Test-Path -LiteralPath $venvPython)) {
            $result = Invoke-PythonCandidate $selectedPython.Executable $selectedPython.PrefixArguments @("-m", "venv", $venvDirectory)
            if ($result -ne 0 -or -not (Test-Path -LiteralPath $venvPython)) {
                throw "Не удалось создать .venv. Проверьте права записи в папку пакета и повторите запуск."
            }
        }

        & $venvPython -m pip install --no-index --find-links $wheelDirectory --upgrade --force-reinstall excel-transform-1c
        if ($LASTEXITCODE -ne 0) {
            throw "Не удалось установить компоненты из локальной папки wheels. Распакуйте ZIP заново в новую папку."
        }
        Copy-Item -LiteralPath $packageMarker -Destination $venvMarker -Force
    }

    & $venvPython -c "import excel_transform_1c, fastapi, openpyxl, msoffcrypto; print('Компоненты приложения проверены.')"
    if ($LASTEXITCODE -ne 0) {
        throw "Проверка установленных компонентов завершилась ошибкой. Удалите .venv и повторите запуск."
    }

    $runtimeDirectory = if ($env:OPIU_RUNTIME_DIR) { $env:OPIU_RUNTIME_DIR } else { Join-Path $root "runtime" }
    New-Item -ItemType Directory -Path $runtimeDirectory -Force | Out-Null
    $env:EXCEL_TRANSFORM_RUNTIME = $runtimeDirectory
    $env:PYTHONUTF8 = "1"

    $candidatePorts = New-Object 'System.Collections.Generic.List[int]'
    if ($env:OPIU_PORT) {
        $candidatePorts.Add([int]$env:OPIU_PORT)
    }
    foreach ($fallbackPort in @(8000, 8765, 8001, 8010, 8080)) {
        if (-not $candidatePorts.Contains($fallbackPort)) {
            $candidatePorts.Add($fallbackPort)
        }
    }

    $port = $null
    foreach ($candidatePort in $candidatePorts) {
        if (-not (Test-TcpPort $candidatePort)) {
            $port = $candidatePort
            break
        }
        Write-Host "Порт $candidatePort занят; проверяю следующий."
    }
    if (-not $port) {
        throw "Не найден свободный локальный порт. Закройте старые окна сервиса и повторите запуск."
    }

    $baseUrl = "http://127.0.0.1:$port"
    $healthUrl = "$baseUrl/health"
    $serverArguments = @(
        "-m", "uvicorn", "excel_transform_1c.main:app",
        "--host", "127.0.0.1",
        "--port", "$port"
    )

    if ($SmokeTest) {
        Write-Stage "Проверка упакованного сервиса"
        $serverProcess = Start-Process -FilePath $venvPython -ArgumentList $serverArguments -PassThru -WindowStyle Hidden
        try {
            if (-not (Wait-ServiceReady $healthUrl 80)) {
                throw "Упакованный сервис не ответил на /health."
            }
            $homeResponse = Invoke-WebRequest -UseBasicParsing -Uri "$baseUrl/" -TimeoutSec 5
            if ($homeResponse.StatusCode -ne 200 -or $homeResponse.Content -notmatch "OPIU") {
                throw "Главная страница упакованного сервиса не прошла проверку."
            }
            Write-Host "Пакетный smoke PASS: $baseUrl"
        } finally {
            if ($serverProcess -and -not $serverProcess.HasExited) {
                Stop-Process -Id $serverProcess.Id -Force
            }
        }
    } else {
        Write-Stage "Сервис запускается"
        Write-Host "Адрес: $baseUrl"
        Write-Host "Папка данных: $runtimeDirectory"
        Write-Host "Для остановки нажмите Ctrl+C в этом окне."
        Write-Host "Если браузер не откроется автоматически, откройте адрес вручную."

        $browserCommand = @"
`$healthUrl = '$healthUrl'
`$baseUrl = '$baseUrl'
for (`$attempt = 0; `$attempt -lt 100; `$attempt++) {
    try {
        `$response = Invoke-RestMethod -Uri `$healthUrl -TimeoutSec 1
        if (`$response.status -eq 'ok') {
            Start-Process `$baseUrl
            exit 0
        }
    } catch {
    }
    Start-Sleep -Milliseconds 500
}
exit 1
"@
        $encodedBrowserCommand = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($browserCommand))
        Start-Process powershell.exe -WindowStyle Hidden -ArgumentList @(
            "-NoProfile",
            "-WindowStyle", "Hidden",
            "-EncodedCommand", $encodedBrowserCommand
        ) | Out-Null

        & $venvPython @serverArguments
        if ($LASTEXITCODE -ne 0) {
            throw "Сервер завершился с кодом $LASTEXITCODE."
        }
    }
} catch {
    $exitCode = 1
    Write-Host ""
    Write-Host "СЕРВИС НЕ ЗАПУЩЕН" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "Подробности: $logPath"
    try {
        Add-Content -LiteralPath $logPath -Encoding UTF8 -Value ("ERROR: " + $_.Exception.ToString())
    } catch {
    }
    if (-not $SmokeTest -and $env:OPIU_NONINTERACTIVE -ne "1") {
        Read-Host "Нажмите Enter, чтобы закрыть окно"
    }
} finally {
    if ($transcriptStarted) {
        try {
            Stop-Transcript | Out-Null
        } catch {
        }
    }
}

exit $exitCode
