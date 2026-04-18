$ErrorActionPreference = "Stop"

# Backend port
$BACKEND_PORT = 8010
# Frontend port (default Vite)
$FRONTEND_PORT = 5173

# Function to check if port is listening
function Test-Port {
    param([int]$Port)
    $tcp = New-Object System.Net.Sockets.TcpClient
    try {
        $tcp.Connect("127.0.0.1", $Port)
        $tcp.Close()
        return $true
    } catch {
        return $false
    }
}

<#
Function: Stop-ProcessTree
Parameters:
    ProcessId (int): Target parent process id. Must be a positive integer.
Return:
  void: No return value.
Description:
  Terminates the target process and all child processes recursively.
#>
function Stop-ProcessTree {
    param([int]$ProcessId)

    if ($ProcessId -le 0) {
        return
    }

    $children = Get-CimInstance Win32_Process -Filter "ParentProcessId = $ProcessId" -ErrorAction SilentlyContinue
    foreach ($child in $children) {
        Stop-ProcessTree -ProcessId $child.ProcessId
    }

    Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
}

$backend = $null
$frontend = $null

try {
    # Start backend
    $backend = Start-Process powershell -ArgumentList "-NoExit", "-Command", "python .\CarePal-yolo\api_server.py" -PassThru -WindowStyle Normal

    # Start frontend
    $frontend = Start-Process powershell -ArgumentList "-NoExit", "-Command", "npm run dev:h5" -PassThru -WindowStyle Normal

    Write-Host "Backend started (PID: $($backend.Id))"
    Write-Host "Frontend started (PID: $($frontend.Id))"
    Write-Host "Waiting for services to be ready..."

    # Wait for backend
    while (-not (Test-Port -Port $BACKEND_PORT)) {
        Start-Sleep -Milliseconds 500
    }
    Write-Host "Backend ready on port $BACKEND_PORT"

    # Wait for frontend
    while (-not (Test-Port -Port $FRONTEND_PORT)) {
        Start-Sleep -Milliseconds 500
    }
    Write-Host "Frontend ready on port $FRONTEND_PORT"

    # Open browser
    Write-Host "Opening browser..."
    Start-Process "http://localhost:$FRONTEND_PORT"

    Write-Host "Press Ctrl+C or any key to stop services and exit"

    # Wait for user input to stop
    $null = $Host.UI.RawUI.ReadKey("NoEcho, IncludeKeyDown")
}
finally {
    if ($backend) {
        Stop-ProcessTree -ProcessId $backend.Id
    }
    if ($frontend) {
        Stop-ProcessTree -ProcessId $frontend.Id
    }
    Write-Host "Services stopped"
}
