param(
  [Parameter(Mandatory = $false)]
  [string]$ProjectRef,

  [Parameter(Mandatory = $false)]
  [int]$TimeoutSeconds = 900
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Read-Token {
  param([string]$Path)
  if (-not (Test-Path $Path)) { return "" }
  return (Get-Content -Raw -Path $Path).Trim()
}

function Infer-ProjectRefFromConfig {
  param([string]$ConfigPath)
  if (-not (Test-Path $ConfigPath)) { return "" }
  $raw = Get-Content -Raw -Path $ConfigPath
  $m = [regex]::Match($raw, '^\s*project_id\s*=\s*\"([a-z0-9]+)\"', [System.Text.RegularExpressions.RegexOptions]::Multiline)
  if (-not $m.Success) { return "" }
  return $m.Groups[1].Value
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path
$tokenPath = Join-Path $repoRoot "supabase/supabase_access.token"
$token = Read-Token $tokenPath
if (-not $token) {
  throw "supabase_access.token 为空或不存在：$tokenPath"
}

if (-not $ProjectRef) {
  $ProjectRef = Infer-ProjectRefFromConfig (Join-Path $repoRoot "supabase/config.toml")
}
if (-not $ProjectRef) {
  throw "缺少 ProjectRef。请传入 -ProjectRef 或确保 supabase/config.toml 有 project_id。"
}

$base = "https://api.supabase.com/v1/projects/$ProjectRef"
$headers = @{ Authorization = "Bearer $token" }

function Get-ProjectStatus {
  $p = Invoke-RestMethod -Method Get -Uri $base -Headers $headers
  return [string]$p.status
}

function Wait-ForStatus {
  param(
    [string[]]$Wanted,
    [int]$TimeoutSeconds
  )
  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    $s = Get-ProjectStatus
    Write-Host ("status=" + $s)
    if ($Wanted -contains $s) { return $s }
    Start-Sleep -Seconds 10
  }
  throw "超时：未等到目标状态：$($Wanted -join ', ')"
}

Write-Host ("project=" + $ProjectRef)
Write-Host ("before=" + (Get-ProjectStatus))

Write-Host "POST /pause"
Invoke-RestMethod -Method Post -Uri ($base + "/pause") -Headers $headers | Out-Null
Wait-ForStatus @("INACTIVE") $TimeoutSeconds | Out-Null

Write-Host "POST /restore"
Invoke-RestMethod -Method Post -Uri ($base + "/restore") -Headers $headers | Out-Null
Wait-ForStatus @("ACTIVE_HEALTHY", "ACTIVE_UNHEALTHY") $TimeoutSeconds | Out-Null

Write-Host ("after=" + (Get-ProjectStatus))

