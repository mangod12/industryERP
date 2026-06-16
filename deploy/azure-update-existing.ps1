param(
    [string]$ResourceGroup = "rg-industryerp-prod",
    [string]$WebAppName = "industryerp-06161244878",
    [string]$AcrName = "industryerpacr06161244878",
    [string]$ImageName = "industryerp",
    [string]$ImageTag = ""
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    throw "Azure CLI was not found in PATH."
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker was not found. Start Docker Desktop before deploying."
}

if (-not $ImageTag) {
    if (Get-Command git -ErrorAction SilentlyContinue) {
        $ImageTag = (& git rev-parse --short HEAD 2>$null).Trim()
    }
    if (-not $ImageTag) {
        $ImageTag = Get-Date -Format "yyyyMMddHHmmss"
    }
}

function Invoke-Az {
    & az @args
    if ($LASTEXITCODE -ne 0) {
        throw "Azure CLI command failed: az $($args -join ' ')"
    }
}

$loginServer = Invoke-Az acr show --resource-group $ResourceGroup --name $AcrName --query loginServer -o tsv
$image = "$loginServer/$ImageName`:$ImageTag"

Write-Host "[azure] Updating existing Web App"
Write-Host "[azure] Resource group: $ResourceGroup"
Write-Host "[azure] Web App: $WebAppName"
Write-Host "[azure] Image: $image"

Invoke-Az acr login --name $AcrName | Out-Null

Write-Host "[azure] Building container image"
docker build -t $image .
if ($LASTEXITCODE -ne 0) {
    throw "Docker build failed."
}

Write-Host "[azure] Pushing container image"
docker push $image
if ($LASTEXITCODE -ne 0) {
    throw "Docker push failed."
}

Write-Host "[azure] Pointing Web App at the updated image"
Invoke-Az webapp config container set `
    --resource-group $ResourceGroup `
    --name $WebAppName `
    --container-image-name $image | Out-Null

Write-Host "[azure] Restarting Web App"
Invoke-Az webapp restart --resource-group $ResourceGroup --name $WebAppName | Out-Null

$appUrl = "https://$WebAppName.azurewebsites.net"
Write-Host "[azure] Waiting for health at $appUrl/healthz"

for ($i = 0; $i -lt 60; $i++) {
    try {
        $health = Invoke-RestMethod -Uri "$appUrl/healthz" -TimeoutSec 10
        $version = Invoke-RestMethod -Uri "$appUrl/version" -TimeoutSec 10
        if ($health.status -eq "ok") {
            Write-Host "[azure] Healthy. Version: $($version.version)"
            Write-Host "[azure] URL: $appUrl"
            exit 0
        }
    } catch {
        Start-Sleep -Seconds 5
    }
}

throw "Azure app did not become healthy within the expected time."
