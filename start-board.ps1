$ErrorActionPreference = 'Stop'
$taskPort = $null
foreach ($taskCandidate in 8765..8774) {
    $taskCandidateUrl = "http://127.0.0.1:$taskCandidate/"
    try {
        $taskHealth = Invoke-RestMethod -Uri ($taskCandidateUrl + 'api/health') -TimeoutSec 1
        if ($taskHealth.app -eq 'tactics-board' -and $taskHealth.workspace -eq $PSScriptRoot) {
            Start-Process $taskCandidateUrl
            exit 0
        }
    } catch { }
    $taskClient = New-Object System.Net.Sockets.TcpClient
    try {
        $taskConnection = $taskClient.ConnectAsync('127.0.0.1', $taskCandidate)
        $taskConnected = $taskConnection.Wait(300) -and $taskClient.Connected
    } catch { $taskConnected = $false }
    finally { $taskClient.Dispose() }
    if (!$taskConnected) { $taskPort = $taskCandidate; break }
}
if ($null -eq $taskPort) { throw 'Ports 8765-8774 are in use. Close an unused board and try again.' }
$taskUrl = "http://127.0.0.1:$taskPort/"
$taskPythonArgs = @()
$taskPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if (!(Test-Path -LiteralPath $taskPython)) {
    $taskPyLauncher = Get-Command py -ErrorAction SilentlyContinue
    $taskPythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($taskPyLauncher) { $taskPython = $taskPyLauncher.Source; $taskPythonArgs = @('-3') }
    elseif ($taskPythonCommand -and $taskPythonCommand.Source -notmatch 'WindowsApps') { $taskPython = $taskPythonCommand.Source }
    else { throw 'Python 3 was not found. Open index.html directly, or install Python 3 to use live OBS updates.' }
}
$taskServer = Join-Path $PSScriptRoot 'board-server.py'
$taskPythonArgs += @(('"' + $taskServer + '"'), '--port', "$taskPort")
Start-Process -FilePath $taskPython -ArgumentList $taskPythonArgs -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
for ($taskTry = 0; $taskTry -lt 30; $taskTry++) {
    Start-Sleep -Milliseconds 200
    try {
        $taskHealth = Invoke-RestMethod -Uri ($taskUrl + 'api/health') -TimeoutSec 1
        if ($taskHealth.app -eq 'tactics-board' -and $taskHealth.workspace -eq $PSScriptRoot) { Start-Process $taskUrl; exit 0 }
    } catch { }
}
throw 'Unable to start the local board. Check that Python 3 is available.'
