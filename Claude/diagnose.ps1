# Quick diagnostic: ping every layer and report what's working.
#   .\diagnose.ps1
$ErrorActionPreference = "Continue"

function Ok($m)   { Write-Host "[OK]   $m" -ForegroundColor Green }
function Fail($m) { Write-Host "[FAIL] $m" -ForegroundColor Red }
function Warn($m) { Write-Host "[WARN] $m" -ForegroundColor Yellow }
function Info($m) { Write-Host "       $m" -ForegroundColor DarkGray }

Write-Host "`n== Layer 1: Ollama ==" -ForegroundColor Cyan
try {
    $tags = Invoke-RestMethod "http://127.0.0.1:11434/api/tags" -TimeoutSec 5
    Ok "Ollama responding on :11434"
    $models = $tags.models | ForEach-Object { $_.name }
    Info "Pulled models: $($models -join ', ')"
    foreach ($m in @("llama3.1:8b","llama3.2:3b","qwen2.5:3b")) {
        if ($models -contains $m) { Ok "  $m present" }
        else { Warn "  $m NOT pulled" }
    }
} catch {
    Fail "Ollama not responding: $_"
    Info "Fix: open a new terminal and run 'ollama serve'"
    exit 1
}

Write-Host "`n== Layer 2: Ollama can actually generate ==" -ForegroundColor Cyan
$payload = @{
    model = "llama3.1:8b"
    prompt = "Reply with the single word 'OK'."
    stream = $false
    options = @{ num_predict = 5 }
} | ConvertTo-Json
try {
    $t0 = Get-Date
    $r = Invoke-RestMethod "http://127.0.0.1:11434/api/generate" `
        -Method POST -Body $payload -ContentType "application/json" -TimeoutSec 120
    $dt = (New-TimeSpan -Start $t0).TotalSeconds
    Ok "llama3.1:8b generated in $($dt.ToString('F1'))s: '$($r.response.Trim())'"
    if ($dt -gt 30) {
        Warn "  Slow first response is normal (model loading into RAM)."
        Warn "  Subsequent calls should be much faster."
    }
} catch {
    Fail "llama3.1:8b generation failed: $_"
    Info "Likely cause: model not pulled, or not enough RAM (8B needs ~5GB)."
    Info "Workaround: 'ollama pull llama3.2:3b' and pick it in Settings -> Model."
}

Write-Host "`n== Layer 3: Backend health ==" -ForegroundColor Cyan
try {
    $h = Invoke-RestMethod "http://127.0.0.1:8000/health" -TimeoutSec 5
    Ok "Backend responding"
    Info "  store_ready: $($h.components.vectorstore.status)"
    Info "  llm backend: $($h.components.llm.status)"
    Info "  embedder:    $($h.components.embedder.status)"
} catch {
    Fail "Backend not responding on :8000: $_"
    exit 2
}

Write-Host "`n== Layer 4: End-to-end /api/chat ==" -ForegroundColor Cyan
$body = @{
    message = "Apa visi UPI?"
    top_k = 3
    model = "llama3.1:8b"
} | ConvertTo-Json
try {
    $t0 = Get-Date
    $r = Invoke-RestMethod "http://127.0.0.1:8000/api/chat" `
        -Method POST -Body $body -ContentType "application/json" -TimeoutSec 180
    $dt = (New-TimeSpan -Start $t0).TotalSeconds
    Ok "/api/chat succeeded in $($dt.ToString('F1'))s, backend used = $($r.backend)"
    Info "  Answer preview: $($r.answer.Substring(0, [Math]::Min(120, $r.answer.Length)))..."
    Info "  $($r.sources.Count) sources returned"
} catch {
    Fail "/api/chat failed: $_"
    Info "Look at the backend PowerShell window for the Python traceback."
}

Write-Host "`nDone.`n"
