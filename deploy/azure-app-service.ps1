param(
    [string]$ResourceGroup = "rg-industryerp-prod",
    [string]$Location = "southeastasia",
    [string]$AppPrefix = "industryerp",
    [string]$AdminEmail = "anshajkumar341@gmail.com",
    [string]$AdminUsername = "admin",
    [string]$Sku = "B1",
    [string]$PostgresSku = "Standard_B1ms",
    [string]$ImageTag = "prod"
)

$ErrorActionPreference = "Stop"

function New-RandomText([int]$Length, [string]$Alphabet) {
    -join (1..$Length | ForEach-Object { $Alphabet[(Get-Random -Minimum 0 -Maximum $Alphabet.Length)] })
}

if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    throw "Azure CLI was not found in PATH. Install it, then open a new terminal."
}

function Invoke-Az {
    & az @args
    if ($LASTEXITCODE -ne 0) {
        throw "Azure CLI command failed: az $($args -join ' ')"
    }
}

function Wait-AzureProvider([string]$Namespace) {
    Invoke-Az provider register --namespace $Namespace | Out-Null
    for ($i = 0; $i -lt 60; $i++) {
        $state = Invoke-Az provider show --namespace $Namespace --query registrationState -o tsv
        if ($state -eq "Registered") {
            return
        }
        Start-Sleep -Seconds 10
    }
    throw "Provider $Namespace did not finish registration in time."
}

$account = Invoke-Az account show --query user.name -o tsv 2>$null
if (-not $account) {
    throw "Azure CLI is not logged in. Run: az login --use-device-code, then sign in as $AdminEmail"
}

$suffix = (Get-Date -Format "MMddHHmm") + (Get-Random -Minimum 100 -Maximum 999)
$appName = "$AppPrefix-$suffix"
$planName = "$AppPrefix-plan-$suffix"
$acrName = "$($AppPrefix.Replace('-', ''))acr$suffix".ToLowerInvariant()
$postgresName = "$AppPrefix-pg-$suffix"
$databaseName = "industryerp"
$dbAdminUser = "erpadmin"
$dbAdminPassword = "Aa1!" + (New-RandomText 28 "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789") # pragma: allowlist secret
$adminPassword = "Aa1!" + (New-RandomText 28 "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789") # pragma: allowlist secret
$secretKey = New-RandomText 96 "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789" # pragma: allowlist secret

Add-Type -AssemblyName System.Web
$dbPasswordEncoded = [System.Web.HttpUtility]::UrlEncode($dbAdminPassword)

Write-Host "[azure] Subscription account: $account"
Write-Host "[azure] Registering required resource providers"
Wait-AzureProvider "Microsoft.ContainerRegistry"
Wait-AzureProvider "Microsoft.DBforPostgreSQL"
Wait-AzureProvider "Microsoft.Web"

$groupExists = Invoke-Az group exists --name $ResourceGroup
if ($groupExists -eq "true") {
    Write-Host "[azure] Using existing resource group $ResourceGroup"
} else {
    Write-Host "[azure] Creating resource group $ResourceGroup in $Location"
    Invoke-Az group create --name $ResourceGroup --location $Location | Out-Null
}

Write-Host "[azure] Creating PostgreSQL Flexible Server $postgresName"
Invoke-Az postgres flexible-server create `
    --resource-group $ResourceGroup `
    --name $postgresName `
    --location $Location `
    --admin-user $dbAdminUser `
    --admin-password $dbAdminPassword `
    --sku-name $PostgresSku `
    --tier Burstable `
    --storage-size 32 `
    --version 16 `
    --public-access 0.0.0.0 `
    --yes | Out-Null

Invoke-Az postgres flexible-server db create `
    --resource-group $ResourceGroup `
    --server-name $postgresName `
    --name $databaseName | Out-Null

$databaseUrl = "postgresql://$dbAdminUser`:$dbPasswordEncoded@$postgresName.postgres.database.azure.com:5432/$databaseName`?sslmode=require"

Write-Host "[azure] Creating Azure Container Registry $acrName"
Invoke-Az acr create --resource-group $ResourceGroup --name $acrName --sku Basic --admin-enabled false | Out-Null
$loginServer = Invoke-Az acr show --resource-group $ResourceGroup --name $acrName --query loginServer -o tsv
$imageName = "$loginServer/industryerp:$ImageTag"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker was not found. Start Docker Desktop before deploying to Azure."
}

Write-Host "[azure] Building container image locally: $imageName"
& docker build -t $imageName .
if ($LASTEXITCODE -ne 0) {
    throw "Docker build failed."
}

Write-Host "[azure] Pushing image to Azure Container Registry"
Invoke-Az acr login --name $acrName | Out-Null
& docker push $imageName
if ($LASTEXITCODE -ne 0) {
    throw "Docker push failed."
}

Write-Host "[azure] Creating Linux App Service plan $planName"
Invoke-Az appservice plan create --resource-group $ResourceGroup --name $planName --location $Location --is-linux --sku $Sku | Out-Null

Write-Host "[azure] Creating Web App $appName"
Invoke-Az webapp create `
    --resource-group $ResourceGroup `
    --plan $planName `
    --name $appName `
    --deployment-container-image-name "mcr.microsoft.com/appsvc/staticsite:latest" | Out-Null

Write-Host "[azure] Granting the Web App managed identity access to ACR"
$principalId = Invoke-Az webapp identity assign --resource-group $ResourceGroup --name $appName --query principalId -o tsv
$acrId = Invoke-Az acr show --resource-group $ResourceGroup --name $acrName --query id -o tsv
Invoke-Az role assignment create --assignee $principalId --scope $acrId --role AcrPull | Out-Null
$webConfigId = Invoke-Az webapp config show --resource-group $ResourceGroup --name $appName --query id -o tsv
Invoke-Az resource update --ids $webConfigId --set properties.acrUseManagedIdentityCreds=True | Out-Null
Invoke-Az webapp config container set --resource-group $ResourceGroup --name $appName --container-image-name $imageName | Out-Null

$appUrl = "https://$appName.azurewebsites.net"
Write-Host "[azure] Setting production app settings"
Invoke-Az webapp config appsettings set `
    --resource-group $ResourceGroup `
    --name $appName `
    --settings `
        "ENVIRONMENT=production" `
        "PORT=8080" `
        "WEBSITES_PORT=8080" `
        "WEB_CONCURRENCY=2" `
        "DATABASE_URL=$databaseUrl" `
        "KUMAR_SECRET_KEY=$secretKey" `
        "CORS_ORIGINS=$appUrl" `
        "ADMIN_USERNAME=$AdminUsername" `
        "ADMIN_EMAIL=$AdminEmail" `
        "ADMIN_PASSWORD=$adminPassword" `
        "ADMIN_ROLE=Boss" `
        "ADMIN_COMPANY=Kumar Brothers Steel" | Out-Null

Write-Host "[azure] Restarting app and checking health"
Invoke-Az webapp restart --resource-group $ResourceGroup --name $appName | Out-Null

$healthy = $false
for ($i = 0; $i -lt 60; $i++) {
    try {
        $response = Invoke-RestMethod -Uri "$appUrl/healthz" -TimeoutSec 10
        if ($response.status -eq "ok") {
            Write-Host "[azure] Health check passed."
            $healthy = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 5
    }
}

if (-not $healthy) {
    throw "Azure app did not become healthy at $appUrl/healthz within the expected time."
}

Write-Host ""
Write-Host "Azure deployment complete"
Write-Host "URL: $appUrl"
Write-Host "Resource group: $ResourceGroup"
Write-Host "Web app: $appName"
Write-Host "PostgreSQL server: $postgresName"
Write-Host "Admin username: $AdminUsername"
Write-Host "Admin email: $AdminEmail"
Write-Host ""
Write-Host "Admin password was generated and stored in the App Service settings. Retrieve or rotate it through Azure, not logs."
