# Queue candidate verification on Kaggle (private): refresh harness + candidates datasets, push kernel.
# Usage: powershell -File tools\kaggle_verify.ps1 -Jobs data\candidates\job.json -Message "why"
# job.json lists candidate dirs under data\candidates (see kaggle\verify_kernel\run.py).
param(
    [Parameter(Mandatory = $true)][string]$Jobs,
    [string]$Message = "update"
)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$k = ".venv\Scripts\kaggle.exe"

# Harness dataset: harness/*.py + current baseline cache.
$hs = "kaggle\harness_ds\harness"
if (Test-Path $hs) { Remove-Item -Recurse -Force $hs }
New-Item -ItemType Directory -Force $hs | Out-Null
Copy-Item harness\*.py $hs
Copy-Item ledger\baseline_costs.json $hs
& $k datasets version -p kaggle\harness_ds --dir-mode zip -m $Message
if (-not $?) { throw "harness dataset version failed" }

# Candidates dataset: only the dirs named in job.json, plus job.json itself.
$cs = "kaggle\candidates_ds"
Get-ChildItem $cs -Exclude dataset-metadata.json -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
$job = Get-Content $Jobs -Raw | ConvertFrom-Json
foreach ($j in $job.jobs) {
    if ($j.submission -ne "REFERENCE") { Copy-Item -Recurse "data\candidates\$($j.submission)" "$cs\$($j.submission)" }
}
Copy-Item $Jobs "$cs\job.json"
$exists = (& $k datasets list -m -s vqcc-candidates) -match "vqcc-candidates"
if ($exists) { & $k datasets version -p $cs --dir-mode zip -m $Message } else { & $k datasets create -p $cs --dir-mode zip }
if (-not $?) { throw "candidates dataset upload failed" }

& $k kernels push -p kaggle\verify_kernel
