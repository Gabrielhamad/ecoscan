$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (Test-Path -LiteralPath $python) {
    & $python scripts\run_delivery_demo.py serve @args
} else {
    & py -3.12 scripts\run_delivery_demo.py serve @args
}
if ($LASTEXITCODE -ne 0) { throw "Confira README_EXECUCAO.md e Python 3.12." }
