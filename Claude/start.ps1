# =============================================================================
# UPI RAG Chatbot - one-shot launcher
# =============================================================================
# Starts Ollama (if not already), the FastAPI backend, the Next.js frontend,
# then opens http://localhost:3000 in your default browser.
#
# Each service runs in its OWN PowerShell window so you can read its logs and
# Ctrl+C it independently. Closing this launcher window does NOT kill them.
#
# Usage:
#   .\start.ps1            # start everything, open browser
#   .\start.ps1 -NoOpen    # start everything, don't open browser
#   .\start.ps1 -Status    # report what's running, then exit
#   .\start.ps1 -Stop      # kill running backend + frontend windows
# =============================================================================
[CmdletBinding()]
param(
    [switch]$NoOpen,
    [switch]$Status,
    [switch]$Stop,
    [string]$BackendPort = "8000",
    [string]$FrontendPort = "3000",
    [string]$DefaultModel = "llama3.1:8b"
)

$ErrorActionPreference = "Stop"
$Root      = $PSScriptRoot
$Backend   = Join-Path $Root "backend"
$Frontend  = Join-Path $Root "frontend"
$LogDir    = Join-Path $Root "logs"
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

function Info($m)    { Write-Host "[info] $m"    -ForegroundColor Cyan }
function Ok($m)      { Write-Host "[ok]   $m"    -ForegroundColor Green }
function Warn($m)    { Write-Host "[warn] $m"    -ForegroundColor Yellow }
function Err($m)     { Write-Host "[fail] $m"    -ForegroundColor Red }

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
function Test-Port($p) {
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $async = $tcp.BeginConnect("127.0.0.1", [int]$p, $null, $null)
        $waited = $async.AsyncWaitHandle.WaitOne(400)
        if ($waited -and $tcp.Connected) { $tcp.Close(); return $true }
        $tcp.Close(); return $false
    } catch { return $false }
}

function Test-Url($u) {
    try {
        $r = Invoke-WebRequest -Uri $u -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        return ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500)
    } catch { return $false }
}

function Get-ProcessOnPort($p) {
    try {
        $conn = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction Stop |
                Select-Object -First 1
        return Get-Process -Id $conn.OwningProcess -ErrorAction Stop
    } catch { return $null }
}

# ---------------------------------------------------------------------------
# Status command
# ---------------------------------------------------------------------------
if ($Status) {
    Info "Status report"
    foreach ($svc in @(
        @{ Name="Ollama";    Port=11434; Url="http://127.0.0.1:11434/api/tags" },
        @{ Name="Backend";   Port=$BackendPort;  Url="http://127.0.0.1:$BackendPort/health" },
        @{ Name="Frontend";  Port=$FrontendPort; Url="http://127.0.0.1:$FrontendPort" }
    )) {
        $up = Test-Port $svc.Port
        if ($up) {
            $proc = Get-ProcessOnPort $svc.Port
            $pidLabel = if ($proc) { "PID $($proc.Id) ($($proc.ProcessName))" } else { "PID unknown" }
            Ok "$($svc.Name) UP on port $($svc.Port) - $pidLabel"
            if (-not (Test-Url $svc.Url)) {
                Warn "  $($svc.Name) port open but $($svc.Url) not responding (may be starting)"
            }
        } else {
            Warn "$($svc.Name) DOWN (port $($svc.Port) not listening)"
        }
    }
    exit 0
}

# ---------------------------------------------------------------------------
# Stop command
# ---------------------------------------------------------------------------
if ($Stop) {
    Info "Stopping backend (port $BackendPort) and frontend (port $FrontendPort)"
    foreach ($p in @($BackendPort, $FrontendPort)) {
        $proc = Get-ProcessOnPort $p
        if ($proc) {
            Info "Killing PID $($proc.Id) ($($proc.ProcessName)) on port $p"
            try { Stop-Process -Id $proc.Id -Force -ErrorAction Stop; Ok "killed" }
            catch { Err "could not kill: $_" }
        } else {
            Info "nothing listening on port $p"
        }
    }
    Warn "Note: Ollama is left running (it's a system service); use 'ollama stop' to stop it"
    exit 0
}

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
Info "UPI RAG Chatbot launcher"
Info "Root: $Root"

# 1. Backend venv exists
$BackendVenvPython = Join-Path $Backend ".venv\Scripts\python.exe"
if (-not (Test-Path $BackendVenvPython)) {
    Err "Backend venv not found at $BackendVenvPython"
    Info "Create it once:"
    Info "  cd `"$Backend`""
    Info "  python -m venv .venv"
    Info "  .\.venv\Scripts\Activate.ps1"
    Info "  pip install -r requirements.txt"
    exit 1
}
Ok "Backend venv present"

# 2. Backend .env exists
if (-not (Test-Path (Join-Path $Backend ".env"))) {
    Warn "Backend .env missing; copying .env.example -> .env"
    Copy-Item (Join-Path $Backend ".env.example") (Join-Path $Backend ".env")
    Warn "Edit .env to point at your FAISS index, then re-run this launcher."
    exit 1
}
Ok "Backend .env present"

# 3. Frontend node_modules
if (-not (Test-Path (Join-Path $Frontend "node_modules"))) {
    Err "Frontend node_modules missing"
    Info "Run once:  cd `"$Frontend`" ; npm install"
    exit 1
}
Ok "Frontend node_modules present"

# 4. Frontend .env.local
if (-not (Test-Path (Join-Path $Frontend ".env.local"))) {
    Warn "Frontend .env.local missing; copying .env.example -> .env.local"
    Copy-Item (Join-Path $Frontend ".env.example") (Join-Path $Frontend ".env.local")
}
Ok "Frontend .env.local present"

# 5. Ollama installed
$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollama) {
    Err "Ollama not on PATH. Install from https://ollama.com/download/windows"
    exit 1
}
Ok "Ollama on PATH"

# ---------------------------------------------------------------------------
# Ollama
# ---------------------------------------------------------------------------
if (Test-Url "http://127.0.0.1:11434/api/tags") {
    Ok "Ollama already running on :11434"
} else {
    Info "Starting Ollama in a new window..."
    $oCmd = "Write-Host 'Ollama serve - keep this window open' -ForegroundColor Cyan; ollama serve"
    Start-Process powershell -ArgumentList "-NoExit","-Command",$oCmd -WindowStyle Normal
    # Wait up to 8s for it to come up
    $ready = $false
    for ($i=0; $i -lt 16; $i++) {
        Start-Sleep -Milliseconds 500
        if (Test-Url "http://127.0.0.1:11434/api/tags") { $ready = $true; break }
    }
    if ($ready) { Ok "Ollama up" } else { Warn "Ollama did not respond in 8s; continuing anyway" }
}

# Check the default model is pulled. Warn (don't fail) if not.
try {
    $tags = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 5
    $names = $tags.models | ForEach-Object { $_.name }
    if ($names -contains $DefaultModel) {
        Ok "Default model '$DefaultModel' is pulled"
    } else {
        Warn "Default model '$DefaultModel' not pulled. Run:  ollama pull $DefaultModel"
        Info "Currently pulled: $($names -join ', ')"
    }
} catch {
    Warn "Could not list Ollama models ($_)"
}

# ---------------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------------
if (Test-Port $BackendPort) {
    $proc = Get-ProcessOnPort $BackendPort
    Warn "Port $BackendPort already in use (PID $($proc.Id) $($proc.ProcessName)); skipping backend launch"
} else {
    Info "Starting backend (uvicorn) on :$BackendPort..."
    $beCmd = @"
Write-Host 'UPI RAG backend - port $BackendPort' -ForegroundColor Cyan
Set-Location '$Backend'
& '$BackendVenvPython' -m uvicorn app.main:app --reload --port $BackendPort
"@
    Start-Process powershell -ArgumentList "-NoExit","-Command",$beCmd -WindowStyle Normal
}

# Wait for backend /health (allows up to 60s — embedder takes a few sec to load)
Info "Waiting for backend /health ..."
$beReady = $false
for ($i=0; $i -lt 120; $i++) {
    Start-Sleep -Milliseconds 500
    if (Test-Url "http://127.0.0.1:$BackendPort/health") { $beReady = $true; break }
}
if ($beReady) { Ok "Backend healthy on :$BackendPort" }
else { Warn "Backend not healthy after 60s; check its window for errors" }

# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------
if (Test-Port $FrontendPort) {
    $proc = Get-ProcessOnPort $FrontendPort
    Warn "Port $FrontendPort already in use (PID $($proc.Id) $($proc.ProcessName)); skipping frontend launch"
} else {
    Info "Starting frontend (next dev) on :$FrontendPort..."
    $feCmd = @"
Write-Host 'UPI RAG frontend - port $FrontendPort' -ForegroundColor Cyan
Set-Location '$Frontend'
npm run dev
"@
    Start-Process powershell -ArgumentList "-NoExit","-Command",$feCmd -WindowStyle Normal
}

# Wait for frontend
Info "Waiting for frontend ..."
$feReady = $false
for ($i=0; $i -lt 120; $i++) {
    Start-Sleep -Milliseconds 500
    if (Test-Url "http://127.0.0.1:$FrontendPort") { $feReady = $true; break }
}
if ($feReady) { Ok "Frontend ready on :$FrontendPort" }
else { Warn "Frontend not ready after 60s; check its window" }

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
Write-Host ""
Ok "UPI RAG Chatbot is up:"
Info "  Frontend  : http://localhost:$FrontendPort"
Info "  Backend   : http://localhost:$BackendPort  (docs: /docs)"
Info "  Ollama    : http://localhost:11434"
Write-Host ""
Info "Stop everything later with:  .\start.ps1 -Stop"
Info "Status check:                .\start.ps1 -Status"

if (-not $NoOpen) {
    Start-Sleep -Seconds 1
    Start-Process "http://localhost:$FrontendPort"
}
